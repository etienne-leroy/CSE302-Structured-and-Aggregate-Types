# --------------------------------------------------------------------
import dataclasses as dc
import enum

from typing import Optional as Opt

# ====================================================================
# Parse tree / Abstract Syntax Tree

# --------------------------------------------------------------------
class Type(enum.Enum):
    VOID = 0
    BOOL = 1
    INT  = 2
    NULL = 3


    
    def __str__(self):
        match self:
            case self.VOID:
                return 'void'
            case self.INT:
                return 'int'
            case self.BOOL:
                return 'bool'
            case self.POINTER:
                return 'pointer'
            case self.ARRAY:
                return 'array'

# --------------------------------------------------------------------
@dc.dataclass
class Range:
    start: tuple[int, int]
    end: tuple[int, int]

    @staticmethod
    def of_position(line: int, column: int):
        return Range((line, column), (line, column+1))

# --------------------------------------------------------------------
@dc.dataclass
class AST:
    position: Opt[Range] = dc.field(kw_only = True, default = None)


# --------------------------------------------------------------------
@dc.dataclass
class Name(AST):
    value: str

########################################################################

@dc.dataclass
class Pointer(Type):
    element_type: Type
    
    def __str__(self):
        return f"{self.element_type}*"

@dc.dataclass
class Array(Type):
    element_type: Type
    size: int
    
    def __str__(self):
        return f"{self.element_type}[{self.element_type}]"

########################################################################

# --------------------------------------------------------------------
@dc.dataclass
class Expression(AST):
    type_: Opt[Type] = dc.field(kw_only = True, default = None)

# --------------------------------------------------------------------
@dc.dataclass
class VarExpression(Expression):
    name: Name


# --------------------------------------------------------------------
@dc.dataclass
class BoolExpression(Expression):
    value: bool

# --------------------------------------------------------------------
@dc.dataclass
class IntExpression(Expression):
    value: int

########################################################################
######### New classes for expression

@dc.dataclass
class NullExpression(Expression):
    type_: None


@dc.dataclass
class ReferenceExpression(Expression):
    value: Expression
    

@dc.dataclass
class DereferenceExpression(Expression):
    pointer_expr: Expression  # Expression that results in a pointer

@dc.dataclass
class AccessExpression(Expression):
    array_expr: Expression  # Expression to access (e.g., array or pointer)
    index: Expression         # int used as an index or key

@dc.dataclass
class AllocateExpression(Expression):
    size: Expression
    alloc_type : Type



    
##########  
########################################################################

# --------------------------------------------------------------------
@dc.dataclass
class OpAppExpression(Expression):
    operator: str
    arguments: list[Expression]

# --------------------------------------------------------------------
@dc.dataclass
class CallExpression(Expression):
    proc: Name
    arguments: list[Expression]

# --------------------------------------------------------------------
@dc.dataclass
class PrintExpression(Expression):
    argument: Expression

# --------------------------------------------------------------------
class Statement(AST):
    pass

# --------------------------------------------------------------------
@dc.dataclass
class VarDeclStatement(Statement):
    name: Name
    init: Expression
    type_: Type

# --------------------------------------------------------------------
@dc.dataclass
class AssignStatement(Statement):
    lhs: Name
    rhs: Expression

# --------------------------------------------------------------------
@dc.dataclass
class ExprStatement(Statement):
    expression: Expression

# --------------------------------------------------------------------
@dc.dataclass
class PrintStatement(Statement):
    value: Expression

# --------------------------------------------------------------------
@dc.dataclass
class BlockStatement(Statement):
    body: list[Statement]

# --------------------------------------------------------------------
@dc.dataclass
class IfStatement(Statement):
    condition: Expression
    then: Statement
    else_: Opt[Statement] = None

# --------------------------------------------------------------------
@dc.dataclass
class WhileStatement(Statement):
    condition: Expression
    body: Statement

# --------------------------------------------------------------------
@dc.dataclass
class BreakStatement(Statement):
    pass

# --------------------------------------------------------------------
@dc.dataclass
class ContinueStatement(Statement):
    pass

# --------------------------------------------------------------------
@dc.dataclass
class ReturnStatement(Statement):
    expr: Opt[Expression]

# --------------------------------------------------------------------
class TopDecl(AST):
    pass

# --------------------------------------------------------------------
@dc.dataclass
class GlobVarDecl(TopDecl):
    name: Name
    init: Expression
    type_: Type

#--------------------------------------------------------------------
@dc.dataclass
class ProcDecl(TopDecl):
    name: Name
    arguments: list[tuple[Name, Type]]
    rettype: Opt[Type]
    body: Statement

# --------------------------------------------------------------------








Block   = list[Statement]
Program = list[TopDecl]
