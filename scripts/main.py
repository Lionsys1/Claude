"""
Lionsys Opportunity Monitor — main entry point.
Runs all scrapers, scores results, sends email alert.
"""

import os
import sys

from fedtech import scrape as scrape_fedtech, get_new as new_fedtech, save as save_fedtech
from subnet import scrape as scrape_subnet, get_new as new_subnet, save as save_subnet
from sam_gov import scrape as scrape_sam, get_new as new_sam, save as save_sam
from scoring import filter_and_score
from emailer import send_email


def main():
    print("=== Lionsys Opportunity Monitor ===")

    all_new = []

    # --- FedTech ---
    print("[1/3] Checking FedTech...")
    fedtech_current = scrape_fedtech()
    fedtech_new = new_fedtech(fedtech_current)
    save_fedtech(fedtech_current)
    print(f"      Found {len(fedtech_new)} new FedTech programs.")
    all_new.extend(fedtech_new)

    # --- SBA SUBNet ---
    print("[2/3] Checking SBA SUBNet...")
    subnet_current = scrape_subnet()
    subnet_new = new_subnet(subnet_current)
    save_subnet(subnet_current)
    print(f"      Found {len(subnet_new)} new SUBNet opportunities.")
    all_new.extend(subnet_new)

    # --- SAM.gov (only if API key provided) ---
    sam_key = os.environ.get("SAM_GOV_API_KEY", "")
    if sam_key:
        print("[3/3] Checking SAM.gov...")
        sam_current = scrape_sam(sam_key)
        sam_new = new_sam(sam_current)
        save_sam(sam_current)
        print(f"      Found {len(sam_new)} new SAM.gov opportunities.")
        all_new.extend(sam_new)
    else:
        print("[3/3] SAM.gov skipped (no SAM_GOV_API_KEY set).")

    # --- Score & filter ---
    print(f"\nScoring {len(all_new)} total new items...")
    relevant = filter_and_score(all_new)
    print(f"Relevant after scoring: {len(relevant)}")

    # --- Email ---
    print("Sending email...")
    send_email(relevant)
    print("Done.")

    # Exit 0 even if nothing found — don't fail the workflow
    sys.exit(0)


if __name__ == "__main__":
    main()
