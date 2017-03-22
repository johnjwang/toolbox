import sys

from dcfparser import DcfFile

def main():
    if len(sys.argv) != 4:
        print("Usage: dcfdiff.py <left.dcf> <right.dcf> <out.csv>")
        sys.exit(1)

    left = DcfFile(sys.argv[1])
    right = DcfFile(sys.argv[2])
    left.to_diff(right, sys.argv[3])

if __name__ == '__main__':
    main()
