#!/usr/bin/env python3
"""Trim trailing spaces from files using the unix utility `sed`.

trim.py --apply file1.txt file2.txt  # apply changes immediately, editing files in place
trim.py --preview file1.txt file2.txt  # preview changes only
trim.py --help # full commandline interface documentation

When --format='git', `git` will also be called.
When --format='fancy', both `git` and `grep` will be called.
"""
import argparse
import subprocess


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "-a",
        "--apply",
        action="store_true",
        help="Immediately trim trailing spaces from all files specified, using sed.",
    )
    modes.add_argument(
        "-p",
        "--preview",
        action="store_true",
        help="Print a preview highlighting trailing spaces that would be trimmed by apply.",
    )
    parser.add_argument(
        "-f",
        "--format",
        default="fancy",
        choices=["git", "fancy", "sed"],
        help="Preview as either unprocessed git diff, with 'fancy' formatting (trimming extraneous information from the git diff), or just print the raw sed output. The default is 'fancy'.",
    )
    parser.add_argument(
        "-c",
        "--color",
        default=1,
        type=int,
        choices=[0, 1, 2, 3, 4, 5, 6, 7],
        help="Pass a color number to use for 'fancy' preview format. Has no effect with other formats. The default is 1, which is red in my terminal.",
    )
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()
    if args.apply:
        for file_name in args.files:
            subprocess.run(f"sed -i 's/[ ]*$//' {file_name}", shell=True)
    elif args.preview:
        for file_name in args.files:
            if args.format == "fancy":
                subprocess.run(
                    (
                        f"sed 's/[ ]*$//' {file_name}"
                        f" | git --no-pager diff --color --no-index -- - {file_name}"
                        f" | grep -v '^.\[31m-'"
                        f" | grep -v '^.\[1mindex'"
                        f" | grep -v '^.\[1m---'"
                        f" | grep -v '^.\[1m+++'"
                        f" | sed 's/diff --git a\/- b\//file: /'"
                        f" | sed 's/^.\[32m+/ /'"
                        f" | sed 's/.\[32m//'"
                        f" | sed 's/\[41m/\[4{args.color}m/'"
                    ),
                    shell=True,
                )
            elif args.format == "git":
                subprocess.run(
                    (
                        f"sed 's/[ ]*$//' {file_name}"
                        f" | git --no-pager diff --color --no-index -- - {file_name}"
                    ),
                    shell=True,
                )
            elif args.format == "sed":
                subprocess.run(f"sed 's/[ ]*$//' {file_name}", shell=True)
    else:
        parser.print_help()
        print(
            "files selected:"
            + "\n\t"
            + "\n\t".join(args.files)
            + "\n"
        )


if __name__ == "__main__":
    main()
