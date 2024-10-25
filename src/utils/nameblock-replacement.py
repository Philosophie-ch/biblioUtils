import csv
from dataclasses import dataclass
from typing import Generic, List, LiteralString, TypeVar

T = TypeVar('T')

@dataclass
class Ok(Generic[T]):
  out: T

@dataclass
class Err:
  message: str


# Define here the delimiter used to separate nameblocks in the raw_nameblocks column
NAMEBLOCKS_DELIMITER = ' and '


def raw_nameblock_parser(raw_nameblocks: str) -> List[str]:
  """
  Nameblocks have this structure: "Lastname, Firstname and Lastname2, Firstname2 and Lastname3, Firstname3 ...". The parser must split this string into a list of strings, where each string is a nameblock.
  """
  split = raw_nameblocks.split(NAMEBLOCKS_DELIMITER)
  stripped = [name.strip() for name in split]
  return stripped


def nameblock_formatter(nameblock: List[str]) -> str:
  """
  The formatter must take a list of strings and return a string with the following structure: "Lastname, Firstname and Lastname2, Firstname2 and Lastname3, Firstname3 ...".
  """
  return NAMEBLOCKS_DELIMITER.join(nameblock)


def main(
  input_file: str,
  replacement_table_file: str
) -> Ok[LiteralString] | Err:
  try:

    replacement_table = {}
    with open(replacement_table_file, 'r', encoding='utf-16') as f:
      reader = csv.DictReader(f)
      for row in reader:
        replacement_table[row['REPLACE']] = row['WITH']

    with open(input_file, 'r', encoding='utf-16') as f:
      buffer = []
      reader = csv.DictReader(f)
      for row in reader:
          raw_nameblocks = row['raw_nameblocks']
          nameblocks = raw_nameblock_parser(raw_nameblocks)
          replaced_nameblocks = []
          for nameblock in nameblocks:
              if nameblock in replacement_table:
                  replaced_nameblocks.append(replacement_table[nameblock])
              else:
                  replaced_nameblocks.append(nameblock)
          raw_nameblocks_replaced = nameblock_formatter(replaced_nameblocks)
          buffer.append(raw_nameblocks_replaced)

    raw_nameblocks_column = '\n'.join(buffer)


    return Ok(
      out = raw_nameblocks_column
    )
    

  except Exception as e:
    return Err(
      message = f"Unexpected error: {e}"
    )



def cli_presenter(result: Ok[LiteralString] | Err) -> None:

  match result:

    case Ok(out):
      print(out)

    case Err(message):
      print(message)



if __name__ == '__main__':
  import argparse

  parser = argparse.ArgumentParser(description='Replace nameblocks in a CSV file with a replacement table')

  parser.add_argument('-i', '--input', type=str, help='Input CSV file', required=True)
  parser.add_argument('-r', '--replacement-table', type=str, help='Replacement table CSV file', required=True)

  args = parser.parse_args()

  result = main(
    input_file=args.input,
    replacement_table_file=args.replacement_table
  )

  cli_presenter(result)

