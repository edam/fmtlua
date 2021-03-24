import attr

from fmtlua.lexer import Lexer

from . import the


@attr.s
class Process:

	file: str = attr.ib()

	def run( self ):
		if the.verbose >= 1:
			print( f"processing: {self.file}" )

		# read file
		with open( self.file, "r", encoding="utf-8" ) as f:
			data = f.read()

		# tokenise
		ast = Lexer( data ).tokenise()
