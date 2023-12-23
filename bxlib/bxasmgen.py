# --------------------------------------------------------------------
import abc

from .bxtac import *

# --------------------------------------------------------------------
class AsmGen(abc.ABC):
    BACKENDS   = {}

    def __init__(self):
        self._var_sizes = dict()  # Sizes of variables, dict[str, int]
        self._tparams = dict()
        self._temps   = dict()
        self._asm     = []
        self._stack_offset = 0  # Tracks the stack offset in 8-byte units
        
    def _temp(self, temp):
        if temp.startswith('@'):
            return self._format_temp(temp[1:])
        if temp in self._tparams:
            return self._format_param(self._tparams[temp])
    
        var_index = self._temps.get(temp)
        var_size = self._var_sizes.get(temp) 
        
        if not var_index and not var_size:    
            self._stack_offset += 1 
            self._temps[temp] = self._stack_offset - 1
            output = self._format_temp(self._stack_offset - 1)  
            
        elif not var_index and var_size is not None:
            shifted_size = var_size >> 3  # RS
            self._stack_offset += shifted_size
            self._temps[temp] = self._stack_offset - 1
            output = self._format_temp(self._stack_offset - 1)  
            
        else:
            output = self._format_temp(var_index)

        return output
    
    def initialize_var_sizes(self, var_sizes):
        self._var_sizes = var_sizes

    @abc.abstractmethod
    def _format_temp(self, index):
        pass

    @abc.abstractmethod
    def _format_param(self, index):
        pass

    def __call__(self, instr: TAC | str):
        if isinstance(instr, str):
            self._asm.append(instr)
            return

        opcode = instr.opcode
        args   = instr.arguments[:]

        if instr.result is not None:
            args.append(instr.result)

        getattr(self, f'_emit_{opcode}')(*args)

    def _get_asm(self, opcode, *args):
        if not args:
            return f'\t{opcode}'
        return f'\t{opcode}\t{", ".join(args)}'

    def _get_label(self, lbl):
        return f'{lbl}:'

    def _emit(self, opcode, *args):
        self._asm.append(self._get_asm(opcode, *args))

    def _emit_label(self, lbl):
        self._asm.append(self._get_label(lbl))

    @classmethod
    def get_backend(cls, name):
        return cls.BACKENDS[name]

# --------------------------------------------------------------------
class AsmGen_x64_Linux(AsmGen):
    PARAMS = ['%rdi', '%rsi', '%rdx', '%rcx', '%r8', '%r9']

    def __init__(self):
        super().__init__()
        self._params = []
        self._endlbl = None

    def _format_temp(self, index):
        if isinstance(index, str):
            return f'{index}(%rip)'
        return f'-{8*(index+1)}(%rbp)'

    def _format_param(self, index):
        return f'{8*(index+2)}(%rbp)'

    def _emit_const(self, ctt, dst):
        self._emit('movq', f'${ctt}', self._temp(dst))

    def _emit_copy(self, src, dst):
        self._emit('movq', self._temp(src), '%r11')
        self._emit('movq', '%r11', self._temp(dst))

    def _emit_alu1(self, opcode, src, dst):
        self._emit('movq', self._temp(src), '%r11')
        self._emit(opcode, '%r11')
        self._emit('movq', '%r11', self._temp(dst))

    def _emit_neg(self, src, dst):
        self._emit_alu1('negq', src, dst)

    def _emit_not(self, src, dst):
        self._emit_alu1('notq', src, dst)

    def _emit_alu2(self, opcode, op1, op2, dst):
        self._emit('movq', self._temp(op1), '%r11')
        self._emit(opcode, self._temp(op2), '%r11')
        self._emit('movq', '%r11', self._temp(dst))

    def _emit_add(self, op1, op2, dst):
        self._emit_alu2('addq', op1, op2, dst)

    def _emit_sub(self, op1, op2, dst):
        self._emit_alu2('subq', op1, op2, dst)

    def _emit_mul(self, op1, op2, dst):
        self._emit('movq', self._temp(op1), '%rax')
        self._emit('imulq', self._temp(op2))
        self._emit('movq', '%rax', self._temp(dst))

    def _emit_div(self, op1, op2, dst):
        self._emit('movq', self._temp(op1), '%rax')
        self._emit('cqto')
        self._emit('idivq', self._temp(op2))
        self._emit('movq', '%rax', self._temp(dst))

    def _emit_mod(self, op1, op2, dst):
        self._emit('movq', self._temp(op1), '%rax')
        self._emit('cqto')
        self._emit('idivq', self._temp(op2))
        self._emit('movq', '%rdx', self._temp(dst))

    def _emit_and(self, op1, op2, dst):
        self._emit_alu2('andq', op1, op2, dst)

    def _emit_or(self, op1, op2, dst):
        self._emit_alu2('orq', op1, op2, dst)

    def _emit_xor(self, op1, op2, dst):
        self._emit_alu2('xorq', op1, op2, dst)

    def _emit_shl(self, op1, op2, dst):
        self._emit('movq', self._temp(op1), '%r11')
        self._emit('movq', self._temp(op2), '%rcx')
        self._emit('salq', '%cl', '%r11')
        self._emit('movq', '%r11', self._temp(dst))

    def _emit_shr(self, op1, op2, dst):
        self._emit('movq', self._temp(op1), '%r11')
        self._emit('movq', self._temp(op2), '%rcx')
        self._emit('sarq', '%cl', '%r11')
        self._emit('movq', '%r11', self._temp(dst))

    def _emit_print(self, arg):
        self._emit('leaq', '.lprintfmt(%rip)', '%rdi')
        self._emit('movq', self._temp(arg), '%rsi')
        self._emit('xorq', '%rax', '%rax')
        self._emit('callq', 'printf@PLT')

    def _emit_jmp(self, lbl):
        self._emit('jmp', lbl)

    def _emit_cjmp(self, cd, op, lbl):
        self._emit('cmpq', '$0', self._temp(op))
        self._emit(cd, lbl)

    def _emit_jz(self, op, lbl):
        self._emit_cjmp('jz', op, lbl)

    def _emit_jnz(self, op, lbl):
        self._emit_cjmp('jnz', op, lbl)

    def _emit_jlt(self, op, lbl):
        self._emit_cjmp('jl', op, lbl)

    def _emit_jle(self, op, lbl):
        self._emit_cjmp('jle', op, lbl)

    def _emit_jgt(self, op, lbl):
        self._emit_cjmp('jg', op, lbl)

    def _emit_jge(self, op, lbl):
        self._emit_cjmp('jge', op, lbl)

    def _emit_param(self, i, arg):
        assert(len(self._params)+1 == i)
        self._params.append(arg)

    def _emit_call(self, lbl, arg, ret = None):
        assert(arg == len(self._params))

        for i, x in enumerate(self._params[:6]):
            self._emit('movq', self._temp(x), self.PARAMS[i])

        qarg = 0 if arg <= 6 else arg - 6

        if qarg & 0x1:
            self._emit('subq', '$8', '%rsp')

        for x in self._params[6:][::-1]:
            self._emit('pushq', self._temp(x))

        self._emit('callq', lbl)

        if qarg > 0:
            self._emit('addq', f'${qarg + qarg & 0x1}', '%rsp')

        if ret is not None:
            self._emit('movq', '%rax', self._temp(ret))

        self._params = []

    def _emit_ret(self, ret = None):
        if ret is not None:
            self._emit('movq', self._temp(ret), '%rax')
        self._emit('jmp', self._endlbl)


    # NEW FUNCTIONS FOR ASSIGNMENT
    def _emit_memory_array_copy(self, target_temp, src_temp, offset):
        
        self._emit("movq", self._temp(src_temp), "%r13")
        self._emit("movq", self._temp(target_temp), "%r14")
        self._emit("movq", f"${offset}", "%r15")

        self._emit("movq", "$0", "%rax") # Zero out %rax when emitting "callq"
        self._emit("callq", "copy_array", "%r14", "%r13", "%r15")

    def _emit_memory_load(self, address, target_register):
        
        (mem_register, offset) = address if isinstance(address, tuple) else (address, 0)
        destination = f"{offset}({mem_register})" if offset != 0 else f"({mem_register})"

        self._emit("movq", self._temp(destination), '%r8')
        self._emit("addq", f"${offset}", "%r8")
        self._emit("movq", "(%r8)", "%r9")
        self._emit("movq", "%r9", self._temp(target_register))
        
    def _emit_memory_store(self, input_data, target_address):
        
        (mem_register, offset) = target_address if isinstance(target_address, tuple) else (target_address, 0)
        destination = f"{offset}({mem_register})" if offset != 0 else f"({mem_register})"
        
        self._emit("movq", self._temp(destination), '%r10')
        self._emit("addq", f"${offset}", "%r10")
        self._emit("movq", self._temp(input_data), "%r11")
        self._emit("movq", "%r11", "(%r10)")
        
    def _emit_memory_pointer(self, source_temp, target_temp):

        self._emit("leaq", self._temp(source_temp), "%r12")
        self._emit("movq", "%r12", self._temp(target_temp))
        
    def _emit_memory_allocation(self, count_temp, size_temp, target_temp):

        self._emit("movq", f"${size_temp}", "%rsi") # Pass first six integer/pointer params to callq
        self._emit("movq", self._temp(count_temp), "%rdi") # Pass first six integer/pointer params to callq

        self._emit("movq", "$0", "%rax")  # Zero out %rax when emitting "callq"
        self._emit("callq", "alloc")
        
        self._emit("movq", "%rax", self._temp(target_temp)) # Fetch output of callq

    def _emit_memory_initialization(self, target_temp, byte_count):
        
        self._emit("movq", f"${byte_count}", "%rsi") # Pass first six integer/pointer params to callq
        self._emit("movq", self._temp(target_temp), "%rdi") # Pass first six integer/pointer params to callq

        self._emit("movq", "$0", "%rax")  # Zero out %rax when emitting "callq"
        self._emit("callq", "zero_out")
        
    # END OF ASSIGNMENT FUNCTIONS
    
    
    @classmethod
    def lower1(cls, tac: TACProc | TACVar) -> list[str]:
        emitter = cls()

        match tac:
            case TACVar(name, init):
                emitter._emit('.data')
                emitter._emit('.globl', name)
                emitter._emit_label(name)
                emitter._emit('.quad', str(init))

                return emitter._asm

            case TACProc(name, arguments, ptac):
                emitter._endlbl = f'.E_{name}'
                emitter.initialize_var_sizes(tac.var_sizes)

                for i in range(min(6, len(arguments))):
                    emitter._emit('movq', emitter.PARAMS[i], emitter._temp(arguments[i]))

                for i, arg in enumerate(arguments[6:]):
                    emitter._tparams[arg] = i

                for instr in ptac:
                    emitter(instr)

                nvars  = len(emitter._temps)
                nvars += nvars & 1

                return [
                    emitter._get_asm('.text'),
                    emitter._get_asm('.globl', name),
                    emitter._get_label(name),
                    emitter._get_asm('pushq', '%rbp'),
                    emitter._get_asm('movq', '%rsp', '%rbp'),
                    emitter._get_asm('subq', f'${8*nvars}', '%rsp'),
                ] + emitter._asm + [
                    emitter._get_label(emitter._endlbl),
                    emitter._get_asm('movq', '%rbp', '%rsp'),
                    emitter._get_asm('popq', '%rbp'),
                    emitter._get_asm('retq'),
                ]

    @classmethod
    def lower(cls, tacs: list[TACProc | TACVar]) -> str:
        aout = [cls.lower1(tac) for tac in tacs]
        aout = [x for tac in aout for x in tac]
        return "\n".join(aout) + "\n"

AsmGen.BACKENDS['x64-linux'] = AsmGen_x64_Linux
