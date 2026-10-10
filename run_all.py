"""Run the model, the figures and the report in one command: model -> figures -> PDF report (report/rebuild/).

Run from the repository root: python run_all.py"""
import subprocess
import sys

for step in (["model/model.py"], ["report/charts.py"], ["report/diagrams.py"], ["report/build.py"]):
    print(f"\n== {step[0]} ==")
    subprocess.run([sys.executable, *step], check=True)
print("\nDone. Report: report/rebuild/Investment_Assessment_rebuild.pdf")
