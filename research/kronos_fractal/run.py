import argparse
from research.kronos_fractal.engine import parse_ticks, save_report, train_and_evaluate
def main():
    p=argparse.ArgumentParser(description="Raw-tick M1 fractal state learner (research only)")
    p.add_argument("--ticks", required=True, help="UTC CSV with timestamp,bid,ask"); p.add_argument("--output", required=True); p.add_argument("--train-ratio", type=float, default=.70)
    a=p.parse_args()
    if not 0 < a.train_ratio < 1: p.error("--train-ratio must be between 0 and 1")
    save_report(train_and_evaluate(parse_ticks(a.ticks), a.train_ratio), a.output); print(a.output)
if __name__ == "__main__": main()
