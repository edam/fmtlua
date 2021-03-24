import getopt
import os
import sys

from fmtlua import the
from fmtlua.process import Process


def _process_commandline():

	try:
		options, args = getopt.gnu_getopt(
			sys.argv[1:],
			"v",
			[
				#"conf=",
				"verbose",
				"help",
			],
		)

		# programme options
		for opt, optarg in options:
			if opt in ["-v", "--verbose"]:
				the.verbose += 1
			elif opt in ["--help"]:
				_print_help()

		# remaining command line args
		list.extend(the.files, args)

		# check for something to do
		if len(the.files) == 0:
			raise the.FatalError( "no input files" )

	except getopt.error as e:
		raise the.FatalError(str(e)) from None


def _print_help():
	# .....01234567890123456789012345678901234567890123456789012345678901234567890123456789
	print("fmtlua")
	print()
	print(f"Usage: {app} [OPTION]... FILE...")
	print()
	print("Options:")
	#print("  -c, --conf=name     specify alternative config file")
	print("  -v, --verbose    say more about what's going on")
	print("      --help       display this help and exit")
	sys.exit(0)


# --

def run():
	try:
		_process_commandline()
		for file in the.files:
			Process(file).run()
	except the.FatalError as e:
		print( f"{the.app}: {str(e)}", file=sys.stderr )
		exit(1)
