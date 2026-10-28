"""
Package all W-SENTRY deliverables into a distributable archive.
Creates: w-sentry-deliverables.zip with paper, results, and code.
"""
import os
import shutil
import json
from pathlib import Path
from datetime import datetime

def package_deliverables():
    """Create deliverables archive."""
    
    base = Path("C:/Users/Riteesh/Programming/w-sentry")
    output_dir = base / "deliverables"
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d")
    package_name = f"w-sentry-deliverables-{timestamp}"
    package_dir = output_dir / package_name
    
    # Clean previous builds
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir()
    
    print(f"Creating deliverables package: {package_name}")
    
    # 1. Paper and figures
    print("\n[1/6] Packaging paper...")
    paper_dir = package_dir / "paper"
    paper_dir.mkdir()
    shutil.copy(base / "paper/w-sentry-paper-draft.md", paper_dir / "w-sentry-paper.md")
    
    figures_dir = paper_dir / "figures"
    figures_dir.mkdir()
    for fig in (base / "paper/figures").glob("*.png"):
        shutil.copy(fig, figures_dir / fig.name)
    shutil.copy(base / "paper/figures/fig1_architecture.html", figures_dir / "fig1_architecture.html")
    shutil.copy(base / "paper/figures/generate_figures.py", figures_dir / "generate_figures.py")
    
    # 2. Results (Phase 1 + Phase 2)
    print("[2/6] Packaging results...")
    results_dir = package_dir / "results"
    results_dir.mkdir()
    shutil.copy(base / "data/processed/phase1_results.json", results_dir / "phase1_results.json")
    shutil.copy(base / "data/processed/phase2_results.json", results_dir / "phase2_results.json")
    
    # 3. Phase 3 implementation plan
    print("[3/6] Packaging Phase 3 plan...")
    docs_dir = package_dir / "docs"
    docs_dir.mkdir()
    shutil.copy(base / "docs/PHASE3_PLAN.md", docs_dir / "PHASE3_PLAN.md")
    
    # 4. Source code
    print("[4/6] Packaging source code...")
    src_dir = package_dir / "src"
    shutil.copytree(base / "src", src_dir, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    
    # 5. Runner scripts
    print("[5/6] Packaging runner scripts...")
    shutil.copy(base / "run_phase1.py", package_dir / "run_phase1.py")
    shutil.copy(base / "run_phase2.py", package_dir / "run_phase2.py")
    shutil.copy(base / "requirements.txt", package_dir / "requirements.txt")
    
    # 6. README and documentation
    print("[6/6] Packaging documentation...")
    shutil.copy(base / "README.md", package_dir / "README.md")
    shutil.copy(base / "LICENSE", package_dir / "LICENSE")
    
    # Create manifest
    manifest = {
        "package": package_name,
        "created": datetime.now().isoformat(),
        "contents": {
            "paper": "IEEE conference paper draft + 4 figures",
            "results": "Phase 1 (RF/XGB baselines) + Phase 2 (Hybrid DL + DANN)",
            "source_code": "Complete Python codebase (data, features, models)",
            "phase3_plan": "Dashboard implementation plan (700 lines, 9 tasks)",
            "documentation": "README, LICENSE, setup instructions"
        },
        "metrics": {
            "same_dataset_accuracy": {
                "WSN-DS": "98.1%",
                "CIC-IoT-2023": "97.8%",
                "Edge-IIoTset": "94.4%"
            },
            "cross_dataset_transfer": {
                "WSN_to_Edge": "80.7%",
                "Edge_to_CIC": "61.8%"
            },
            "DANN_2domain": {
                "CIC": "96.5%",
                "Edge": "96.3%"
            }
        },
        "requirements": {
            "python": "3.11+",
            "pytorch": "2.6.0",
            "cuda": "12.1+ (optional, CPU fallback supported)",
            "ram": "8GB minimum, 16GB recommended"
        }
    }
    
    with open(package_dir / "MANIFEST.json", "w") as f:
        json.dump(manifest, f, indent=2)
    
    # Create ZIP archive
    print("\nCreating ZIP archive...")
    archive_path = output_dir / f"{package_name}"
    shutil.make_archive(str(archive_path), 'zip', output_dir, package_name)
    
    # Cleanup temp directory
    shutil.rmtree(package_dir)
    
    archive_file = f"{archive_path}.zip"
    size_mb = os.path.getsize(archive_file) / (1024 * 1024)
    
    print(f"\n✓ Package created: {archive_file}")
    print(f"  Size: {size_mb:.2f} MB")
    print(f"\n📦 Contents:")
    print(f"  • Paper draft + 4 figures")
    print(f"  • Phase 1+2 results (JSON)")
    print(f"  • Complete source code")
    print(f"  • Phase 3 implementation plan")
    print(f"  • README + LICENSE")
    print(f"\nReady for distribution! 🚀")
    
    return archive_file

if __name__ == "__main__":
    package_deliverables()
