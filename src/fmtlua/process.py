import attr

from . import the


@attr.s
class Process:

	file: str = attr.ib()

	def run( self ):
		if the.verbose >= 1:
			print( f"processing: {self.file}" )
