"""Offline regression tests; run with python -m unittest discover -s tests."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills' / 'transcribe' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import transcribe

spec = importlib.util.spec_from_file_location('transcribe_launcher', SCRIPTS / 'run.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class SetupTests(unittest.TestCase):
    def test_cpu_never_probes_nvidia(self):
        with patch.object(launcher.subprocess, 'run', side_effect=AssertionError('probe')):
            self.assertFalse(launcher.cuda_requested('cpu'))

    def test_auto_detects_nvidia_driver(self):
        with patch.object(launcher.sys, 'platform', 'linux'), patch.object(
                launcher.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'GPU\n')):
            self.assertTrue(launcher.cuda_requested('auto'))

    def test_missing_nvidia_tool_uses_cpu(self):
        with patch.object(launcher.sys, 'platform', 'linux'), patch.object(
                launcher.subprocess, 'run', side_effect=FileNotFoundError):
            self.assertFalse(launcher.cuda_requested('auto'))

    def test_macos_auto_uses_cpu(self):
        with patch.object(launcher.sys, 'platform', 'darwin'):
            self.assertFalse(launcher.cuda_requested('auto'))

    def test_explicit_cuda_on_mac_is_actionable(self):
        with patch.object(launcher.sys, 'platform', 'darwin'):
            with self.assertRaisesRegex(ValueError, 'CUDA.*macOS'):
                launcher.cuda_requested('cuda')

    def test_help_does_not_create_environment(self):
        with patch.object(launcher, 'ensure_venv', side_effect=AssertionError('install')):
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
                launcher.main(['--help'])
            self.assertEqual(result.exception.code, 0)

    def test_invalid_options_do_not_create_environment(self):
        with patch.object(launcher, 'ensure_venv', side_effect=AssertionError('install')):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
                launcher.main(['video.mp4', '--device', 'metal'])
            self.assertEqual(result.exception.code, 2)

    def test_setup_selects_requirements_and_reuses_stamp(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(
                os.environ, {'TRANSCRIBE_VENV': folder}), patch.object(
                launcher.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
            py = launcher.venv_python(Path(folder))
            py.parent.mkdir(parents=True)
            py.touch()
            launcher.ensure_venv(False)
            installs = [c.args[0] for c in run.call_args_list if '-r' in c.args[0]]
            self.assertEqual(Path(installs[-1][installs[-1].index('-r') + 1]).name, 'requirements.txt')
            run.reset_mock()
            launcher.ensure_venv(False)
            self.assertEqual(run.call_count, 0)
            launcher.ensure_venv(True)
            installs = [c.args[0] for c in run.call_args_list if '-r' in c.args[0]]
            self.assertEqual(Path(installs[-1][installs[-1].index('-r') + 1]).name, 'requirements-cuda.txt')

    def test_cuda_stamp_covers_base_and_cuda_requirements(self):
        with tempfile.TemporaryDirectory() as folder:
            base, cuda = Path(folder) / 'base.txt', Path(folder) / 'cuda.txt'
            base.write_text('base-one')
            cuda.write_text('cuda-one')
            with patch.object(launcher, 'REQUIREMENTS', base), patch.object(launcher, 'CUDA_REQUIREMENTS', cuda):
                cpu_stamp = launcher.requirements_hash(False)
                cuda_stamp = launcher.requirements_hash(True)
                cuda.write_text('cuda-two')
                self.assertEqual(cpu_stamp, launcher.requirements_hash(False))
                self.assertNotEqual(cuda_stamp, launcher.requirements_hash(True))
                cuda_stamp = launcher.requirements_hash(True)
                base.write_text('base-two')
                self.assertNotEqual(cuda_stamp, launcher.requirements_hash(True))


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.media = Path(self.temp.name) / 'talk.wav'
        self.media.touch()
        self.ct2 = types.SimpleNamespace(
            get_cuda_device_count=lambda: 0,
            get_supported_compute_types=lambda device: {'int8', 'float32'} if device == 'cpu'
            else {'float16', 'int8_float16', 'float32'})
        self.whisper = types.SimpleNamespace(WhisperModel=self.make_model)
        modules = patch.dict(sys.modules, {'ctranslate2': self.ct2, 'faster_whisper': self.whisper})
        modules.start()
        self.addCleanup(modules.stop)
        for redirect in (contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO())):
            redirect.__enter__()
            self.addCleanup(redirect.__exit__, None, None, None)

    def make_model(self, name, device, compute_type):
        if compute_type not in {'auto', 'default'} | self.ct2.get_supported_compute_types(device):
            raise ValueError('unsupported compute type')
        def decode(*args, **kwargs):
            def segments():
                if device == 'cuda':
                    yield types.SimpleNamespace(text='partial GPU result', start=0, end=1)
                    raise RuntimeError('cuDNN failed during decoding')
                yield types.SimpleNamespace(text='CPU transcript', start=0, end=2.5)
            return segments(), types.SimpleNamespace(language='en', language_probability=1, duration=3)
        return types.SimpleNamespace(model=types.SimpleNamespace(device=device), transcribe=decode)

    def test_auto_probe_failure_uses_cpu(self):
        self.ct2.get_cuda_device_count = lambda: (_ for _ in ()).throw(RuntimeError('driver unavailable'))
        model = transcribe.load_model('tiny', 'auto', None)
        self.assertEqual(model.model.device, 'cpu')

    def test_auto_cuda_load_failure_resets_precision_on_cpu(self):
        self.ct2.get_cuda_device_count = lambda: 1
        def load(name, device, compute_type):
            if device == 'cuda':
                raise RuntimeError('CUDA unavailable')
            return self.make_model(name, device, compute_type)
        self.whisper.WhisperModel = load
        model = transcribe.load_model('tiny', 'auto', 'float16')
        self.assertEqual(model.model.device, 'cpu')

    def test_explicit_cuda_does_not_silently_use_cpu(self):
        def load(name, device, compute_type):
            if device == 'cuda':
                raise RuntimeError('CUDA unavailable')
            return self.make_model(name, device, compute_type)
        self.whisper.WhisperModel = load
        with self.assertRaisesRegex(RuntimeError, 'CUDA'):
            transcribe.load_model('tiny', 'cuda', None)

    def test_unsupported_cpu_precision_has_useful_error(self):
        with self.assertRaisesRegex(ValueError, 'float16.*cpu.*Supported'):
            transcribe.load_model('tiny', 'cpu', 'float16')

    def test_backend_auto_precision_remains_supported(self):
        for precision in ('auto', 'default'):
            with self.subTest(precision=precision):
                self.assertEqual(transcribe.load_model('tiny', 'cpu', precision).model.device, 'cpu')

    def test_auto_cuda_lazy_failure_retries_cpu(self):
        self.ct2.get_cuda_device_count = lambda: 1
        self.assertEqual(transcribe.main([str(self.media), '--compute-type', 'float16']), 0)
        self.assertEqual(self.media.with_name('talk_raw.txt').read_text(), 'CPU transcript\n')
        self.assertIn('00:00:00,000 --> 00:00:02,500', self.media.with_suffix('.srt').read_text())

    def test_explicit_cuda_lazy_failure_preserves_outputs(self):
        raw, srt = transcribe.output_paths(self.media)
        raw.write_text('original raw')
        srt.write_text('original srt')
        self.assertEqual(transcribe.main([str(self.media), '--device', 'cuda']), 1)
        self.assertEqual(raw.read_text(), 'original raw')
        self.assertEqual(srt.read_text(), 'original srt')

    def test_non_cuda_error_does_not_retry_cpu(self):
        self.ct2.get_cuda_device_count = lambda: 1
        def load(name, device, compute_type):
            if device == 'cpu':
                self.fail('network error must not trigger CPU fallback')
            raise OSError('model download failed')
        self.whisper.WhisperModel = load
        self.assertEqual(transcribe.main([str(self.media)]), 1)

    def test_corrupt_media_during_decoding_preserves_outputs_without_retry(self):
        self.ct2.get_cuda_device_count = lambda: 1
        raw, srt = transcribe.output_paths(self.media)
        raw.write_text('original raw')
        srt.write_text('original srt')
        def load(name, device, compute_type):
            if device == 'cpu':
                self.fail('corrupt media must not trigger CPU fallback')
            model = self.make_model(name, device, compute_type)
            def decode(*args, **kwargs):
                def segments():
                    yield types.SimpleNamespace(text='partial result', start=0, end=1)
                    raise RuntimeError('invalid media packet')
                return segments(), types.SimpleNamespace(language='en', language_probability=1, duration=3)
            model.transcribe = decode
            return model
        self.whisper.WhisperModel = load
        self.assertEqual(transcribe.main([str(self.media)]), 1)
        self.assertEqual(raw.read_text(), 'original raw')
        self.assertEqual(srt.read_text(), 'original srt')

    def test_collision_rejected_before_skip_or_write(self):
        other = self.media.with_suffix('.mp4')
        other.touch()
        raw, srt = transcribe.output_paths(self.media)
        raw.write_text('original raw')
        srt.write_text('original srt')
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors), patch.object(
                transcribe, 'load_model', side_effect=AssertionError('load before validation')):
            self.assertEqual(transcribe.main([str(self.media), str(other), '--skip-existing']), 1)
        self.assertIn('Output collision', errors.getvalue())
        self.assertEqual(raw.read_text(), 'original raw')
        self.assertEqual(srt.read_text(), 'original srt')

    def test_all_existing_is_success_without_model_load(self):
        for path in transcribe.output_paths(self.media):
            path.touch()
        with patch.object(transcribe, 'load_model', side_effect=AssertionError('unnecessary load')):
            self.assertEqual(transcribe.main([str(self.media), '--skip-existing']), 0)

    def test_missing_inputs_remain_error(self):
        self.assertEqual(transcribe.main([str(self.media.with_name('missing.wav')), '--skip-existing']), 1)


if __name__ == '__main__':
    unittest.main()
