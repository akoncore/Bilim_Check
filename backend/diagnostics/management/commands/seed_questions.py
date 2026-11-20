import json
from pathlib import Path

from django.core.management.base import BaseCommand

from diagnostics.views import import_bank


class Command(BaseCommand):
    help = "Load the bundled question bank on an empty installation."

    def handle(self, *args, **options):
        path = Path(__file__).resolve().parents[3] / "question-bank.json"
        count = import_bank(json.loads(path.read_text(encoding="utf-8")), seed=True)
        self.stdout.write(f"Seeded {count} questions")
