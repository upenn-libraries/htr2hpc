import unittest
from unittest.mock import patch, MagicMock
import pytest

from htr2hpc.train.slurm_jobstats import SlurmJobStats


class TestSlurmJobStats(unittest.TestCase):

    @patch('htr2hpc.train.slurm_jobstats.SlurmJobStats._run_sacct')
    def setUp(self, mock_run_sacct):
        """Set up test fixtures with mocked sacct output."""
        self.mock_sacct_output = """AllocCPUS|End|ElapsedRaw|JobID|MaxRSS|Start
8|2025-09-25T16:37:00|78|570385||2025-09-25T16:35:42
8|2025-09-25T16:37:01|79|570385.batch|1565820K|2025-09-25T16:35:42
8|2025-09-25T16:37:00|78|570385.extern|0|2025-09-25T16:35:42"""

        mock_run_sacct.return_value = self.mock_sacct_output
        self.job_stats = SlurmJobStats(570385)

    def test_initialization(self):
        """Test that SlurmJobStats initializes correctly."""
        self.assertEqual(self.job_stats.job_id, 570385)
        self.assertIsInstance(self.job_stats.stats, list)
        self.assertEqual(len(self.job_stats.stats), 3)

    def test_job_duration(self):
        """Test job_duration returns correct elapsed time."""
        duration = self.job_stats.job_duration()
        self.assertEqual(duration, 79)
        self.assertIsInstance(duration, int)

    def test_num_cpus(self):
        """Test num_cpus returns correct CPU count."""
        cpus = self.job_stats.num_cpus()
        self.assertEqual(cpus, 8)
        self.assertIsInstance(cpus, int)

    def test_max_mem_kilobytes(self):
        """Test max_mem correctly converts kilobytes to gigabytes."""
        max_mem = self.job_stats.max_mem()
        # 1565820K = 1565820 / (1024 * 1024) = ~1.494 GB
        expected = 1565820 / (1024 * 1024)
        self.assertAlmostEqual(max_mem, expected, places=6)

    @patch('htr2hpc.train.slurm_jobstats.SlurmJobStats._run_sacct')
    def test_max_mem_megabytes(self, mock_run_sacct):
        """Test max_mem correctly converts megabytes to gigabytes."""
        mock_output = """AllocCPUS|End|ElapsedRaw|JobID|MaxRSS|Start
8|2025-09-25T16:37:01|79|570385.batch|1500M|2025-09-25T16:35:42"""
        mock_run_sacct.return_value = mock_output

        job_stats = SlurmJobStats(570385)
        max_mem = job_stats.max_mem()
        # 1500M = 1500 / 1024 = ~1.465 GB
        expected = 1500 / 1024
        self.assertAlmostEqual(max_mem, expected, places=6)

    @patch('htr2hpc.train.slurm_jobstats.SlurmJobStats._run_sacct')
    def test_max_mem_gigabytes(self, mock_run_sacct):
        """Test max_mem handles gigabytes correctly."""
        mock_output = """AllocCPUS|End|ElapsedRaw|JobID|MaxRSS|Start
8|2025-09-25T16:37:01|79|570385.batch|2G|2025-09-25T16:35:42"""
        mock_run_sacct.return_value = mock_output

        job_stats = SlurmJobStats(570385)
        max_mem = job_stats.max_mem()
        # 2G = 2 / 1 = 2.0 GB
        expected = 2.0
        self.assertAlmostEqual(max_mem, expected, places=6)

    def test_mem_per_cpu(self):
        """Test mem_per_cpu calculates correctly."""
        mem_per_cpu = self.job_stats.mem_per_cpu()
        expected_max_mem = 1565820 / (1024 * 1024)  # ~1.494 GB
        expected = expected_max_mem / 8  # 8 CPUs
        self.assertAlmostEqual(mem_per_cpu, expected, places=6)

    @patch('htr2hpc.train.slurm_jobstats.SlurmJobStats._run_sacct')
    def test_get_batch_step_missing_batch_job(self, mock_run_sacct):
        """Test that _get_batch_step raises KeyError when batch job is missing."""
        mock_output = """AllocCPUS|End|ElapsedRaw|JobID|MaxRSS|Start
8|2025-09-25T16:37:00|78|570385||2025-09-25T16:35:42
8|2025-09-25T16:37:00|78|570385.extern|0|2025-09-25T16:35:42"""
        mock_run_sacct.return_value = mock_output

        with self.assertRaises(KeyError) as context:
            SlurmJobStats(570385)

        self.assertIn("No job with id 570385.batch found", str(context.exception))

    @patch('htr2hpc.train.slurm_jobstats.subprocess.run')
    def test_run_sacct_command(self, mock_subprocess):
        """Test that _run_sacct calls subprocess with correct parameters."""
        mock_result = MagicMock()
        mock_result.stdout = self.mock_sacct_output
        mock_subprocess.return_value = mock_result

        job_stats = SlurmJobStats(570385)

        mock_subprocess.assert_called_once_with(
            ['sacct', '--jobs=570385', '--format=ALL', '--parsable2'],
            capture_output=True,
            text=True
        )

    def test_batch_step_properties(self):
        """Test that batch_step contains expected properties."""
        batch_step = self.job_stats.batch_step

        self.assertEqual(batch_step['JobID'], '570385.batch')
        self.assertEqual(batch_step['AllocCPUS'], '8')
        self.assertEqual(batch_step['ElapsedRaw'], '79')
        self.assertEqual(batch_step['MaxRSS'], '1565820K')
        self.assertEqual(batch_step['End'], '2025-09-25T16:37:01')
        self.assertEqual(batch_step['Start'], '2025-09-25T16:35:42')

    def test_stats_parsing(self):
        """Test that stats are parsed correctly from CSV."""
        self.assertEqual(len(self.job_stats.stats), 3)

        # Check main job entry
        main_job = next(job for job in self.job_stats.stats if job['JobID'] == '570385')
        self.assertEqual(main_job['AllocCPUS'], '8')
        self.assertEqual(main_job['ElapsedRaw'], '78')
        self.assertEqual(main_job['MaxRSS'], '')  # Empty for main job

        # Check batch job entry
        batch_job = next(job for job in self.job_stats.stats if job['JobID'] == '570385.batch')
        self.assertEqual(batch_job['AllocCPUS'], '8')
        self.assertEqual(batch_job['ElapsedRaw'], '79')
        self.assertEqual(batch_job['MaxRSS'], '1565820K')

        # Check extern job entry
        extern_job = next(job for job in self.job_stats.stats if job['JobID'] == '570385.extern')
        self.assertEqual(extern_job['AllocCPUS'], '8')
        self.assertEqual(extern_job['ElapsedRaw'], '78')
        self.assertEqual(extern_job['MaxRSS'], '0')

    def test__str__(self):
        """Test that __str__ returns expected JSON."""
        expected = """[
  {
    "AllocCPUS": "8",
    "End": "2025-09-25T16:37:00",
    "ElapsedRaw": "78",
    "JobID": "570385",
    "MaxRSS": "",
    "Start": "2025-09-25T16:35:42"
  },
  {
    "AllocCPUS": "8",
    "End": "2025-09-25T16:37:01",
    "ElapsedRaw": "79",
    "JobID": "570385.batch",
    "MaxRSS": "1565820K",
    "Start": "2025-09-25T16:35:42"
  },
  {
    "AllocCPUS": "8",
    "End": "2025-09-25T16:37:00",
    "ElapsedRaw": "78",
    "JobID": "570385.extern",
    "MaxRSS": "0",
    "Start": "2025-09-25T16:35:42"
  }
]"""
        self.assertEqual(str(self.job_stats), expected)

if __name__ == '__main__':
    unittest.main()