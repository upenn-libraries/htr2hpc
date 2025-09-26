import csv
import json
import re
import subprocess
from io import StringIO


class SlurmJobStats:
    def __init__(self, job_id: int) -> None:
        self.job_id: int = job_id
        self.stats: list[dict[str, int]] = self._get_stats()
        self.batch_step: dict[str, str] = self._get_batch_step()

    def job_duration(self) -> int:
        """Return the ElapsedRaw for the batch step in seconds."""
        return int(self.batch_step['ElapsedRaw'])

    def mem_per_cpu(self) -> float:
        """Return average memory usage per CPU in gigabytes."""
        return self.max_mem() / self.num_cpus()

    def max_mem(self) -> float:
        """Return maximum memory usage in gigabytes."""
        max_rss, units = re.findall(r'(\d+)([A-Za-z]+)', self.batch_step['MaxRSS'])[0]

        divisor = 1
        if units.startswith('M'):
            divisor = 1024
        elif units.endswith('K'):
            divisor = 1024 * 1024

        return float(max_rss)/divisor

    def num_cpus(self) -> int:
        """Return number of CPUs allocated."""
        return int(self.batch_step['AllocCPUS'])

    def _get_batch_step(self) -> dict[str, str]:
        """Get the data for JobID {id}.batch. """
        if not self.stats:
            self.stats = self._get_stats()

        for step in self.stats:
            if step['JobID'] == f"{self.job_id}.batch":
                return step

        raise KeyError(f"No job with id {self.job_id}.batch found")

    def _get_stats(self) -> list[dict[str, int]]:
        dict_reader = csv.DictReader(StringIO(self._run_sacct()), delimiter="|")

        return list(dict_reader)

    def _run_sacct(self) -> str:
        result = subprocess.run(
            ['sacct', f"--jobs={self.job_id}", "--format=ALL", "--parsable2"],
            capture_output=True,
            text=True,
        )

        return result.stdout

    def __str__(self):
        return json.dumps(self.stats, indent=2)
