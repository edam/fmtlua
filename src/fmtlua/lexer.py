import functools
import pprint
import re

from . import the


class NoMatch( RuntimeError ):
	pass

class Token():

	def __init__( self, name, match ):
		self.name = name
		self.match = match if name is None else None
		self.kids = match if name is not None else None

	def __repr__( self ):
		if self.name is not None:
			nl = '\n' if self.name == 'statement' else ''
			kids = ', '.join( map( repr, self.kids ) )
			kids = f" {kids} " if kids else ''
			return f"{nl}{self.name}[{kids}]"
		else:
			return f"'{self.match}'"



# alternate: matches exactly one of the ops
# @param_list separate ops (or sequences of)
# @returns list of tokens, or raises NoMatch
def alt( *ops ):
	def fn( self ):
		token = self._token
		if the.verbose >= 4:
			print( f"{self._ind}alt?" )
			self._ind += ' '
		for op in ops:
			try:
				tokens = self._consume( op )
				if the.verbose >= 4:
					self._ind = self._ind[ :-1 ]
					print( f"{self._ind}ALT: found" )
				return tokens
			except NoMatch as e:
				pass
		if the.verbose >= 4:
			self._ind = self._ind[ :-1 ]
			print( f'{self._ind}alt: fail' )
		raise NoMatch()
	return fn

# repeat: matches op sequence zero or more times
# @param_list sequence of ops
# @returns list of tokens, or empty list (doesn't raise NoMatch)
def rep( *ops ):
	def fn( self ):
		tokens, reps = [], 0
		if the.verbose >= 4:
			print( f"{self._ind}rep" )
			self._ind += ' '
		while True:
			try:
				tokens += self._consume( ops )
				reps += 1
			except NoMatch as e:
				if the.verbose >= 4:
					self._ind = self._ind[ :-1 ]
					if reps > 0:
						print( f'{self._ind}REP: found {reps}' )
				return tokens
	return fn

# optional: matches op sequence zero or once
# @param_list sequence of ops
# @returns list of tokens, or empty list (doesn't raise NoMatch)
def opt( *ops ):
	def fn( self ):
		if the.verbose >= 4:
			print( f"{self._ind}opt" )
			self._ind += ' '
		try:
			tokens = self._consume( ops )
			if the.verbose >= 4:
				self._ind = self._ind[ :-1 ]
				print( f'{self._ind}OPT: found' )
			return tokens
		except NoMatch as e:
			if the.verbose >= 4:
				self._ind = self._ind[ :-1 ]
			return []
	return fn

# regex: matches regex
# @param regex regex to match
# @returns list of 1 token, or raises NoMatch
def reg( regex ):
	regex = re.compile( regex )
	def fn( self ):
		if the.verbose >= 4:
			print( f"{self._ind}reg for {self._token}?" )
		m = regex.match( self._data, self._at )
		if m:
			self._set_at( m.end() )
			if the.verbose >= 4:
				print( f"{self._ind}REG: {m.group( 0 )}" )
			elif the.verbose >= 3:
				print( f"lit: {m.group( 0 )}" )
			self._slurp()
			return [ Token( None, m.group( 0 ) ) ]
		else:
			raise NoMatch()
	return fn

# literal: matches literal string
# @param match string to match
# @returns list of 1 token, or raises NoMatch
def lit( match ):
	def fn( self ):
		if the.verbose >= 4:
			print( f"{self._ind}lit {match}?" )
		if self._data[ self._at : self._at + len( match ) ] == match:
			self._set_at( self._at + len( match ) )
			if the.verbose >= 4:
				print( f"{self._ind}LIT: {match}" )
			elif the.verbose >= 3:
				print( f"lit: {match}" )
			self._slurp()
			return [ Token( None, match ) ]
		else:
			raise NoMatch()
	return fn

_symbol_re = re.compile( '[a-zA-Z_][a-zA-Z0-9_]*' )

_keywords = {
	"break", "while", "do", "end", "repeat", "until", "local", "function",
	"goto", "if", "then", "elseif", "else", "for", "in", "or", "and", "not",
	"nil", "true", "false", "return",
}

# a symbol
def symbol():
	def fn( self ):
		if the.verbose >= 4:
			print( f"{self._ind}symbol?" )
		m = _symbol_re.match( self._data, self._at )
		if m and m.group( 0 ) not in _keywords:
			self._set_at( m.end() )
			if the.verbose >= 4:
				print( f"{self._ind}SYMBOL: {m.group( 0 )}" )
			elif the.verbose >= 3:
				print( f"symbol: {m.group( 0 )}" )
			self._slurp()
			return [ Token( None, m.group( 0 ) ) ]
		else:
			raise NoMatch()
	return fn


_grammar = {
	"block": [ rep( "statement" ), opt( "ret_stmt" ) ],
	"statement": alt(
		"while_stmt",
		"repeat_stmt",
		"local_stmt",
		"goto_stmt",
		"if_stmt",
		"for_stmt",
		"func_stmt",
		"assignment",
		"var",
		"label",
		lit( "break" ),
		lit( ";" ),
	),
	"ret_stmt": [ lit( "return" ), opt( "expr_list" ), opt( lit( ";" ) ) ],
	"while_stmt": [ lit( "while" ), "expr", "_do_block" ],
	"_do_block": [ lit( "do" ), "block", lit( "end" ) ],
	"repeat_stmt": [ lit( "repeat" ), "block", lit( "until" ), "expr" ],
	"assignment": [ "var_list", lit( "=" ), "expr_list" ],
	"local_stmt": [ lit( "local" ), alt(
		[ "symbol_list", opt( lit( "=" ), "expr_list" ) ],
		[ lit( "function" ), symbol(), "_func_body" ],
	) ],
	"goto_stmt": [ lit( "goto" ), symbol() ],
	"if_stmt": [ lit( "if" ), "expr", lit( "then" ), "block",
				 rep( lit( "elseif" ), "expr", lit( "then" ), "block" ),
				 opt( lit( "else" ), "block" ), lit( "end" ) ],
	"for_stmt": [ lit( "for" ), alt(
		[ symbol(), lit( "=" ), "expr", lit( "," ), "expr",
		  rep( lit( "," ), "expr" ), "_do_block" ],
		[ "symbol_list", lit( "in" ), "expr_list", "_do_block" ],
	) ],
	"func_stmt": [ lit( "function" ), "func_name", "_func_body" ],
	"func_lit": [ lit( "function" ), "_func_body" ],
	"_func_body": [ lit( "(" ), opt( "func_args" ), lit( ")" ),
					"block", lit( "end" ) ],
	"func_args": alt(
		[ "symbol_list", opt( "list_sep", lit( "..." ) ) ],
		lit( "..." ),
	),
	"func_name": [ symbol(), rep( lit( "." ), symbol() ),
				   opt( lit( ":" ), symbol() ) ],
	"expr": [ "_and_expr", rep( lit( 'or' ), "_and_expr" ) ],
	"_and_expr": [ "_comp_expr", rep( lit( 'and' ), "_comp_expr" ) ],
	"_comp_expr": [ "_cat_expr", opt( reg( '>=|<=|>|<|==|~=' ), "_cat_expr" ) ],
	"_cat_expr": [ "_add_expr", rep( lit( '..' ), "_add_expr" ) ],
	"_add_expr": [ "_mul_expr", rep( reg( '[-+]' ), "_mul_expr" ) ],
	"_mul_expr": [ "_bit_expr", rep( reg( '[*/%]|//' ), "_bit_expr" ) ],
	"_bit_expr": [ "_una_expr", rep( reg( '[&|~]|<<|>>' ), "_una_expr" ) ],
	"_una_expr": alt(
		[ lit( '-' ), "_una_expr" ],
		[ lit( '#' ), "_pow_expr" ],
		[ lit( 'not' ), "_una_expr" ],
		[ lit( '~' ), "_una_expr" ],
		"_pow_expr",
	),
	"_pow_expr": [ "atom", rep( lit( '^' ), "atom" ) ],
	"atom": alt(
		lit( "..." ),
		lit( "nil" ),
		lit( "true" ),
		lit( "false" ),
		"var",
		"func_lit",
		"table",
		"number",
		"string",
	),
	"var": [ alt(
		[ lit( '(' ), "expr", lit( ')' ) ],
		symbol(),
	), rep( "_var_tail" ) ],
	"_var_tail": alt(
		[ lit( '.' ), symbol() ],
		[ lit( '[' ), "expr", lit( ']' ) ],
		[ lit( ':' ), symbol(), lit( '(' ), opt( "expr_list" ), lit( ')' ) ],
		[ lit( ':' ), symbol(), "table" ],
		[ lit( ':' ), symbol(), "string" ],
		[ lit( '(' ), opt( "expr_list" ), lit( ')' ) ],
		"table",
		"string",
	),
	"table": [ lit( '{' ), opt( "field_list" ), lit( '}' ) ],
	"field": alt(
		[ lit( '[' ), "expr", lit( ']' ), lit( '=' ), "expr" ],
		[ symbol(), lit( '=' ), "expr" ],
		"expr",
	),
	"label": [ lit( '::' ), symbol(), lit( '::' ) ],

	"field_list": [ "field", rep( "field_sep", "field" ), opt( "field_sep" ) ],
	"var_list": [ "var", rep( "list_sep", "var" ) ],
	"expr_list": [ "expr", rep( "list_sep", "expr" ) ],
	"symbol_list": [ symbol(), rep( "list_sep", symbol() ) ],

	# literals
	"list_sep": lit( ',' ),
	"field_sep": alt( lit( ',' ), lit( ';' ) ),
	#"symbol": reg( '[a-zA-Z_][a-zA-Z0-9_]*' ),
	"string": reg( '([\'"])(?:\\\\.|(?:(?!\\1).))*\\1' ),
	"number": reg(
		'[0-9]+(?:\\.[0-9]*)?(?:[eE][-+]?[0-9+])?|' +
		'\\.[0-9]+(?:[eE][-+]?[0-9+])?|' +
		'0[xX][0-9a-fA-F](?:\\.[0-9a-fA-F]?)?(?:[pP][-+]?[0-9]+)?'
	),
}


pp = pprint.PrettyPrinter(indent=4)
pp = pprint.pprint

_slurp_re = re.compile( "([ \t]*)(--[^\r\n]*)?(\r\n|\n|\r)?" )


class Lexer:

	def __init__( self, data ):
		self._data = data

	def tokenise( self ):
		self._at = 0
		self._line = 1
		self._line_at = 0
		self._parse_at = 0
		self._parse_line = 1
		self._parse_line_at = 0
		self._ind = ''
		self._slurp()
		tokens = self._consume( "block" )
		ast = tokens[ 0 ] if len( tokens ) else None
		if self._at < len( self._data ):
			regex = re.compile( '[^\r\n]*' )
			line = regex.match( self._data, self._parse_line_at )[ 0 ]
			offset = self._parse_at - self._parse_line_at
			if offset < 50:
				offset = ' ' * offset + '^ here'
			else:
				offset = ' ' * ( offset - 5 ) + 'here ^'
			raise the.FatalError( f'parse error at line {self._parse_line}:\n' +
								  f'> {line}\n' +
								  f'  {offset}' )
		if the.verbose >= 2:
			print( ast )
		return ast


	def _consume( self, op ):
		if( type( op ) == str ):
			if the.verbose >= 4:
				print( f'{self._ind}match "{op}"' )
				self._ind += ' '
			elif the.verbose >= 3:
				print( f'lex: "{op}"' )
			self._token = op
			try:
				tokens = self._consume( _grammar[ op ] )
			except:
				if the.verbose >= 4:
					self._ind = self._ind[ :-1 ]
				raise
			if the.verbose >= 4:
				self._ind = self._ind[ :-1 ]
				print( f'{self._ind}MATCH "{op}"' )
			return tokens if op[ 0 : 1 ] == '_' else [ Token( op, tokens ) ]
		elif( type( op ) == list ):
			ops, at, line = op, self._at, self._line
			try:
				return functools.reduce(
					lambda ret, op: ret + self._consume( op ), ops, [] )
			except NoMatch as e:
				self._at, self._line = at, line
				raise e
			#return seq( *op )( self )
		elif( type( op ) == tuple ):
			return self._consume( list( op ) )
		elif( callable( op ) ):
			return op( self )
		else:
			raise RuntimeError( 'bad op' )

	def _slurp( self ):
		while True:
			m = _slurp_re.match( self._data, self._at )
			if m is not None and m.end() > m.start():
				if the.verbose >= 3:
					print( f'{self._ind}slurp: {repr( m.group( 0 ) )}' )
				self._set_at( m.end() )
				if m.end( 3 ) > m.start( 3 ): # ends in newline?
					self._line += 1
					self._line_at = self._at
					self._parse_line += 1
					self._parse_line_at = self._at
				else:
					break
			else:
				break

	def _set_at( self, at ):
		self._at = at
		self._parse_at = self._at
		self._parse_line = self._line
		self._parse_line_at = self._line_at
