#!/usr/bin/env python3
"""
Check Crossref Submission Status

Query the status of DOI submissions using Crossref's admin API.
This allows you to check submission results when you don't have access to the notification emails.

Usage:
    python check_submission_status.py <batch_id>
    python check_submission_status.py --list-recent

Examples:
    # Check specific batch
    python check_submission_status.py philosophie-update-20251001-173256

    # List recent submissions
    python check_submission_status.py --list-recent
"""

import argparse
import os
import sys
import requests
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from datetime import datetime
import time


def check_submission_status(
    batch_id: str, username: str, password: str, use_sandbox: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Check the status of a submission using Crossref admin API.

    Parameters
    ----------
    batch_id : str
        The batch ID from the submission
    username : str
        Crossref username
    password : str
        Crossref password
    use_sandbox : bool
        Whether to query sandbox environment

    Returns
    -------
    Optional[Dict[str, Any]]
        Submission status information
    """
    if use_sandbox:
        base_url = "https://test.crossref.org"
    else:
        base_url = "https://doi.crossref.org"

    # Crossref admin API endpoint for submission status
    # Crossref tracks submissions by the multipart upload filename, not doi_batch_id.
    # The filename used during upload is typically "{batch_id}.xml".
    url = f"{base_url}/servlet/submissionDownload"

    file_name = batch_id if batch_id.endswith(".xml") else f"{batch_id}.xml"
    params = {"usr": username, "pwd": password, "file_name": file_name, "type": "result"}

    try:
        print(f"🔍 Querying submission status for batch: {batch_id}")
        print(f"   Environment: {'SANDBOX' if use_sandbox else 'PRODUCTION'}")

        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            # Response is XML content
            xml_content = response.text

            # Always dump first 100 lines at the end
            def dump_response() -> None:
                print(f"\n📄 First 100 lines of Crossref response:")
                print(f"{'-'*80}")
                lines = xml_content.split('\n')
                for i, line in enumerate(lines[:100], 1):
                    print(f"{i:3d} | {line}")
                if len(lines) > 100:
                    print(f"... and {len(lines) - 100} more lines")
                print(f"{'-'*80}")

            # Check if submission is actually found
            if 'status="unknown_submission"' in xml_content:
                print("\n⚠️  Submission not found or results not ready yet")
                print("   This is normal if the submission was just made - processing can take 10-30 minutes")
                dump_response()
                return None

            # Parse basic info from XML
            if "batch_id" in xml_content or "doi_batch_diagnostic" in xml_content:
                print("\n✅ Submission found!")

                # Save full response to file
                log_filename = f"submission_status_{batch_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
                with open(log_filename, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
                print(f"\n💾 Full response saved to: {log_filename}")
                print(f"   (Total length: {len(xml_content)} chars)\n")

                # Try to extract key information
                analyze_submission_result(xml_content)

                # Dump response
                dump_response()

                return {"success": True, "xml": xml_content}
            else:
                print("\n⚠️  Unexpected response format")
                dump_response()
                return None

        elif response.status_code == 404:
            print("\n⚠️  Submission not found")
            print("   Possible reasons:")
            print("   - Batch ID is incorrect")
            print("   - Results not available yet (processing takes time)")
            print("   - Querying wrong environment (sandbox vs production)")
            return None
        else:
            print(f"\n❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None

    except requests.RequestException as e:
        print(f"\n❌ Error querying submission status: {e}")
        return None


def analyze_submission_result(xml_content: str) -> None:
    """Parse and display key information from submission result XML."""

    print("\n📊 Analysis:")
    print(f"{'-'*80}")

    # Count successes and failures
    success_count = xml_content.count('<record_diagnostic status="Success"')
    failure_count = xml_content.count('<record_diagnostic status="Failure"')
    warning_count = xml_content.count('<record_diagnostic status="Warning"')

    if success_count > 0:
        print(f"✅ Successful records: {success_count}")
    if warning_count > 0:
        print(f"⚠️  Warnings: {warning_count}")
    if failure_count > 0:
        print(f"❌ Failed records: {failure_count}")

    # Extract error messages if any
    if "Failure" in xml_content or "failure" in xml_content:
        print("\n🔍 Error details:")
        # Simple extraction of msg tags
        import re

        errors = re.findall(r'<msg>(.*?)</msg>', xml_content, re.DOTALL)
        for i, error in enumerate(errors[:100], 1):  # Show first 100 errors
            error_clean = error.strip().replace('\n', ' ')[:200]
            print(f"   {i}. {error_clean}")
        if len(errors) > 100:
            print(f"   ... and {len(errors) - 100} more errors")

    # Check batch status
    if 'batch_status="completed"' in xml_content:
        print("\n✅ Batch processing completed")
    elif 'batch_status="in_progress"' in xml_content:
        print("\n⏳ Batch still processing")

    print(f"{'-'*80}")


def list_recent_batches(file_pattern: str = "batch_update_*.xml") -> List[str]:
    """
    List recent batch IDs from XML files in current directory.

    Returns
    -------
    List[str]
        List of batch IDs found
    """
    import glob
    import re

    batch_ids = []

    # Look for batch XML files
    xml_files = glob.glob(file_pattern)

    for xml_file in xml_files:
        # Extract batch ID from filename
        match = re.search(r'batch_update_(.*?)\.xml', xml_file)
        if match:
            batch_ids.append(match.group(1))

        # Also try to parse from file content
        try:
            with open(xml_file, 'r', encoding='utf-8') as f:
                content = f.read(2000)  # Read first 2000 chars
                batch_match = re.search(r'<doi_batch_id>(.*?)</doi_batch_id>', content)
                if batch_match:
                    batch_id = batch_match.group(1)
                    if batch_id not in batch_ids:
                        batch_ids.append(batch_id)
        except Exception:
            pass

    return sorted(batch_ids, reverse=True)


def main() -> int:
    """Main CLI entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Check Crossref DOI submission status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument('batch_id', nargs='?', help='Batch ID to check (e.g., philosophie-update-20251001-173256)')
    parser.add_argument('--sandbox', action='store_true', help='Query sandbox environment')
    parser.add_argument('--production', action='store_true', help='Query production environment')
    parser.add_argument('--list-recent', action='store_true', help='List recent batch IDs from local XML files')
    parser.add_argument('--wait', type=int, metavar='SECONDS', help='Poll for results every N seconds until available')

    args = parser.parse_args()

    # List recent batches
    if args.list_recent:
        print("📋 Recent batch IDs found in local XML files:\n")
        batch_ids = list_recent_batches()

        if batch_ids:
            for batch_id in batch_ids:
                print(f"   • {batch_id}")
            print(f"\nTo check status: python {sys.argv[0]} <batch_id>")
        else:
            print("   No batch XML files found in current directory")

        return 0

    # Require batch_id for status check
    if not args.batch_id:
        parser.print_help()
        print("\n❌ Error: batch_id is required (or use --list-recent)")
        return 1

    # Get credentials
    username = os.getenv("CROSSREF_USERNAME")
    password = os.getenv("CROSSREF_PASSWORD")
    sandbox_username = os.getenv("CROSSREF_SANDBOX_USERNAME")
    sandbox_password = os.getenv("CROSSREF_SANDBOX_PASSWORD")

    if not username or not password:
        print("❌ Error: Missing credentials!")
        print("Please ensure your .env file contains:")
        print("  CROSSREF_USERNAME=your_username")
        print("  CROSSREF_PASSWORD=your_password")
        return 1

    # Determine environment
    use_sandbox = args.sandbox or not args.production

    # Use appropriate credentials
    if use_sandbox and sandbox_username and sandbox_password:
        query_username = sandbox_username
        query_password = sandbox_password
    else:
        query_username = username
        query_password = password

    # Poll if requested
    if args.wait:
        print(f"⏳ Polling every {args.wait} seconds (Ctrl+C to stop)...")
        attempt = 1
        while True:
            print(f"\n{'='*80}")
            print(f"Attempt #{attempt} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")

            result = check_submission_status(args.batch_id, query_username, query_password, use_sandbox)

            if result and result.get('success'):
                print("\n✅ Results retrieved successfully!")
                return 0

            print(f"\n⏳ Waiting {args.wait} seconds before next attempt...")
            try:
                time.sleep(args.wait)
            except KeyboardInterrupt:
                print("\n\n⚠️  Polling stopped by user")
                return 0

            attempt += 1
    else:
        # Single check
        result = check_submission_status(args.batch_id, query_username, query_password, use_sandbox)

        if result and result.get('success'):
            return 0
        else:
            return 1


if __name__ == "__main__":
    exit(main())
