import os
import sys
from enum import Enum
from tempfile import TemporaryFile

################################################
# For debug option. 
# If you want to debug, set 1, program will show you some informations
# If not, set 0.
################################################
DEBUG = 0

MAX_SYMBOL_TABLE_SIZE = 1024
MEM_TEXT_START = 0x00400000
MEM_DATA_START = 0x10000000
BYTES_PER_WORD = 4
INST_LIST_LEN = 20


################################################
# Additional Components
################################################

class bcolors:
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    ENDC = '\033[0m'


start = '[' + bcolors.BLUE + 'START' + bcolors.ENDC + ']  '
done = '[' + bcolors.YELLOW + 'DONE' + bcolors.ENDC + ']   '
success = '[' + bcolors.GREEN + 'SUCCESS' + bcolors.ENDC + ']'
error = '[' + bcolors.RED + 'ERROR' + bcolors.ENDC + ']  '

pType = [start, done, success, error]


def log(printType, content):
    print(pType[printType] + content)


################################################
# Structure Declaration
################################################

class inst_t:
    def __init__(self, name, op, type, funct):
        self.name = name
        self.op = op
        self.type = type
        self.funct = funct


class symbol_t:
    def __init__(self):
        self.name = 0
        self.address = 0


class section(Enum):
    DATA = 0
    TEXT = 1
    MAX_SIZE = 2


################################################
# Global Variable Declaration
################################################

ADDIU = inst_t("addiu", "001001", "I", "") #name, op, type, funct
ADDU = inst_t("addu",    "000000", 'R', "100001")
AND = inst_t("and",     "000000", 'R', "100100")
ANDI = inst_t("andi",    "001100", 'I', "")
BEQ = inst_t("beq",     "000100", 'I', "")
BNE = inst_t("bne",     "000101", 'I', "")
J = inst_t("j",       "000010", 'J', "")
JAL = inst_t("jal",     "000011", 'J', "")
JR = inst_t("jr",      "000000", 'R', "001000")
LUI = inst_t("lui",     "001111", 'I', "")
LW = inst_t("lw",      "100011", 'I', "")
NOR = inst_t("nor",     "000000", 'R', "100111")
OR = inst_t("or",      "000000", 'R', "100101")
ORI = inst_t("ori",     "001101", 'I', "")
SLTIU = inst_t("sltiu",    "001011", 'I', "")
SLTU = inst_t("sltu",    "000000", 'R', "101011")
SLL = inst_t("sll",     "000000", 'R', "000000")
SRL = inst_t("srl",     "000000", 'R', "000010")
SW = inst_t("sw",      "101011", 'I', "")
SUBU = inst_t("subu",    "000000", 'R', "100011")

inst_list = [ADDIU, ADDU, AND, ANDI, BEQ, BNE, J, JAL, JR,
             LUI, LW, NOR, OR, ORI, SLTIU, SLTU, SLL, SRL, SW, SUBU]

index_dict = {}
for i in range(len(inst_list)):
    index_dict[inst_list[i].name] = i

# Global Symbol Table
symbol_struct = symbol_t()
SYMBOL_TABLE = [symbol_struct] * MAX_SYMBOL_TABLE_SIZE

# For indexing of symbol table
symbol_table_cur_index = 0

# Size of each section
data_section_size = 0
text_section_size = 0


################################################
# Function Declaration - NO NEED TO CHANGE
################################################

# Change file extension form ".s" to ".o"
def change_file_ext(fin_name):
    fname_list = fin_name.split('.')
    fname_list[-1] = 'o'
    fout_name = ('.').join(fname_list)
    return fout_name


# Add symbol to global symbol table
def symbol_table_add_entry(symbol):
    global SYMBOL_TABLE
    global symbol_table_cur_index

    SYMBOL_TABLE[symbol_table_cur_index] = symbol
    symbol_table_cur_index += 1
    if DEBUG:
        log(1, f"{symbol.name}: 0x" + hex(symbol.address)[2:].zfill(8))


# Convert integer number to binary string
def num_to_bits(num, len):
    bit = bin(num & (2**len-1))[2:].zfill(len)
    return bit

################################################
# Function Declaration - FILL THE BLANK AREA
################################################

# Fill the blanks
def make_symbol_table(input):
    size_bit = 0
    address = 0
    data_add_dict = {}
    text_add_dict = {}
    count = 0
    prior_token_name = None
    text_add = MEM_TEXT_START

    # Temporary file stream pointers
    data_seg = None
    text_seg = None

    cur_section = section.MAX_SIZE.value

    # Read each section and put the stream
    lines = input.readlines()
    for line in lines:
        line = line.strip()
        _line = line
        token_line = _line.strip('\n\t').split()
        temp = token_line[0]

        # Check section type
        if temp == ".data":
            cur_section = section.DATA.value
            data_seg = TemporaryFile('w+')
            continue
        elif temp == '.text':
            cur_section = section.TEXT.value
            text_seg = TemporaryFile('w+')
            continue

        # Put the line into each segment stream
        if cur_section == section.DATA.value:
            if len(token_line) == 3:
                num_data = 1
                data_name = token_line[0][:-1]
                data_add_dict[data_name] = [address, num_data]
                prior_token_name = data_name
            elif len(token_line) < 3:
                temp = data_add_dict[prior_token_name]
                temp[1] += 1
            data_seg.write(line)
            data_seg.write('\n')

        elif cur_section == section.TEXT.value:
            if len(token_line) == 1:
                text_name = token_line[0][:-1]
                text_add = text_add + count*4
                text_add_dict[text_name] = text_add # 10진수
                count = 0
                continue
            else:
                count += 1

                if token_line[0] == 'la':
                    data = token_line[2]
                    add = data_add_dict[data]
                    start_add = ten_to_bin(MEM_DATA_START + add[0], 32)

                    if start_add[16:] != '0000000000000000':
                        count += 1

            text_seg.write(line)
            text_seg.write('\n')

        address += BYTES_PER_WORD

    return data_seg, text_seg, data_add_dict, text_add_dict


# Record .text section to output file
def record_text_section(output, data_add_dict, text_add_dict):
    cur_addr = MEM_TEXT_START

    # Point to text_seg stream
    text_seg.seek(0)

    # Print .text section
    lines = text_seg.readlines()
    for line in lines:
        line = line.strip()
        token_line = line.strip('\n\t').split()

        R = ['addu', 'and', 'jr', 'nor', 'or', 'sltu', 'sll', 'srl', 'subu']
        I = ['addiu', 'andi', 'beq', 'bne', 'lui', 'lw', 'ori', 'sltiu', 'sw']
        J = ['j', 'jal']

        name = token_line[0]

        if name == 'la':
            data_name = token_line[2]
            add = data_add_dict[data_name]
            start_add = ten_to_bin(MEM_DATA_START + add[0], 32)

            if start_add[16:] == '0000000000000000':
                idx = index_dict['lui']
                op = inst_list[idx].op
                rt = ten_to_bin(int(token_line[1][1:-1]), 5)
                rs = '00000'
                imm = start_add[:16]
                bin_code = op + rs + rt + imm
                output.write(bin_code)
            else:
                idx = index_dict['lui']
                op = inst_list[idx].op
                rt = ten_to_bin(int(token_line[1][1:-1]), 5)
                rs = '00000'
                imm = start_add[:16]
                bin_code = op + rs + rt + imm
                output.write(bin_code)
                output.write("\n")
                cur_addr += BYTES_PER_WORD

                idx = index_dict['ori']
                op = inst_list[idx].op
                rt = ten_to_bin(int(token_line[1][1:-1]), 5)
                rs = ten_to_bin(int(token_line[1][1:-1]), 5)
                imm = start_add[16:]
                bin_code = op + rs + rt + imm
                output.write(bin_code)

            output.write("\n")
            cur_addr += BYTES_PER_WORD

            continue

        type = 'R' if name in R else 'I' if name in I else 'J' if name in J else ValueError

        idx = index_dict[name]
        op = inst_list[idx].op

        if type == 'R':
            funct = inst_list[idx].funct
            shamt = '00000'

            if name in ('addu', 'and', 'or', 'nor', 'subu', 'sltu'):
                rd = ten_to_bin(int(token_line[1][1:-1]), 5)
                rs = ten_to_bin(int(token_line[2][1:-1]), 5)
                rt = ten_to_bin(int(token_line[3][1:]), 5)

            elif name == 'jr':
                rs = ten_to_bin(int(token_line[1][1:]), 5)
                rt = '00000'
                rd = '00000'

            elif name in ('sll', 'srl'):
                rs = '00000'
                rd = ten_to_bin(int(token_line[1][1:-1]), 5)
                rt = ten_to_bin(int(token_line[2][1:-1]), 5)
                shamt = ten_to_bin(int(token_line[3]), 5)

            bin_code = op + rs + rt + rd + shamt + funct

            if DEBUG:
                log(1, f"0x" + hex(cur_addr)[2:].zfill(
                    8) + f": op: {op} rs:${rs} rt:${rt} rd:${rd} shamt:{shamt} funct:{inst_list[idx].funct}")

        elif type == 'I':
            if name == 'addiu':
                rt = ten_to_bin(int(token_line[1][1:-1]), 5)
                rs = ten_to_bin(int(token_line[2][1:-1]), 5)
                if token_line[3][:2] == '0x':
                    num = token_line[3][2:]
                    imm = hex_to_bin(num, 16)
                else:
                    imm = ten_to_bin(int(token_line[3]), 16)

            elif name == 'andi':
                rt = ten_to_bin(int(token_line[1][1:-1]), 5)
                rs = ten_to_bin(int(token_line[2][1:-1]), 5)
                if token_line[3][:2] == '0x':
                    imm = hex_to_bin(token_line[3], 16)
                else:
                    imm = ten_to_bin(int(token_line[3]), 16)

            elif name in ('bne', 'beq'):
                rs = ten_to_bin(int(token_line[1][1:-1]), 5)
                rt = ten_to_bin(int(token_line[2][1:-1]), 5)
                imm = ten_to_bin(int((text_add_dict[token_line[3]] - cur_addr - 4)/4), 16)

            elif name == 'lui':
                rs = ''.zfill(5)
                rt = ten_to_bin(int(token_line[1][1:-1]), 5)
                if token_line[2][:2] == '0x':
                    imm = hex_to_bin(token_line[2], 16)
                else:
                    imm = ten_to_bin(int(token_line[2]), 16)

            elif name in ('lw', 'sw'):
                rt = ten_to_bin(int(token_line[1][1:-1]), 5)
                imm, rs = token_line[2].split('(')
                rs = ten_to_bin(int(rs[1:-1]), 5)
                imm = ten_to_bin(int(imm), 16)

            elif name == 'ori':
                rt = ten_to_bin(int(token_line[1][1:-1]), 5)
                rs = ten_to_bin(int(token_line[2][1:-1]), 5)
                if token_line[3][:2] == '0x':
                    imm = hex_to_bin(token_line[3], 16)
                else:
                    imm = ten_to_bin(int(token_line[3]),16)

            elif name == 'sltiu':
                rt = ten_to_bin(int(token_line[1][1:-1]), 5)
                rs = ten_to_bin(int(token_line[2][1:-1]), 5)
                imm = ten_to_bin(int(token_line[3]), 16)

            bin_code = op + rs + rt + imm

            if DEBUG:
                log(1, f"0x" + hex(cur_addr)
                    [2:].zfill(8) + f": op:{op} rs:${rs} rt:${rt} imm:0x{imm}")

        elif type == 'J':
            if name in ('j', 'jal'):
                text_name = token_line[1]
                add = text_add_dict[text_name]
                add = add/4
                imm = ten_to_bin(int(add), 26)

            bin_code = op + imm

        else:
            raise ValueError

        output.write(bin_code)
        output.write("\n")
        cur_addr += BYTES_PER_WORD


# Record .data section to output file
def record_data_section(output):
    cur_addr = MEM_DATA_START

    # Point to data segment stream
    data_seg.seek(0)

    # Print .data section
    lines = data_seg.readlines()
    for line in lines:
        line = line.strip()
        token_line = line.strip('\n\t').split()
        num = token_line[-1]
        if num[:2] == '0x':
            seg = hex_to_bin(num, 32)
        else:
            seg = ten_to_bin(int(num), 32)
        output.write(seg)
        output.write('\n')

        if DEBUG:
            log(1, f"0x" + hex(cur_addr)[2:].zfill(8) + f": {line}")

        cur_addr += BYTES_PER_WORD


# Fill the blanks
def make_binary_file(output, data_seg, text_seg, data_add_dict, text_add_dict):
    if DEBUG:
        # print assembly code of text section
        text_seg.seek(0)
        lines = text_seg.readlines()
        for line in lines:
            line = line.strip()

    if DEBUG:
        log(1,
            f"text size: {text_section_size}, data size: {data_section_size}")

    # print text section size
    text_seg.seek(0)
    lines = text_seg.readlines()
    text_len = 0
    for line in lines:
        line = line.strip()
        token_line = line.strip('\n\t').split()
        if token_line[0] == 'la':
            data = token_line[2]
            add = data_add_dict[data]
            start_add = ten_to_bin(MEM_DATA_START + add[0], 32)

            if start_add[16:] != '0000000000000000':
                text_len += 1

        text_len += 1
    text_size_two = ten_to_bin(text_len*4, 32)
    output.write(text_size_two)
    output.write('\n')

    # print data section size
    data_seg.seek(0)
    data_size_ten = len(data_seg.readlines())
    data_size_two = ten_to_bin(data_size_ten*4, 32)
    output.write(data_size_two)
    output.write('\n')

    # Print .text section
    record_text_section(output, data_add_dict, text_add_dict)
    # Print .data section
    record_data_section(output)


def ten_to_bin(num, fill=None):
    # convert 10-> 2
    # and fill out '0' for make [fill]bit
    if num >= 0:
        two = bin(num)
        s = str(two)[2:]
        s = s.zfill(fill)
        return s
    elif num < 0:
        poswidth = len(bin(-num)[2:])
        if 2**(poswidth - 1) ==-num:
            poswidth -= 1

        twocomp = 2**(poswidth + 1) + num
        binary = bin(twocomp)[2:]
        binwidth = len(binary)

        outwidth = max(binwidth, fill)
        s = '1' * (outwidth-binwidth)+binary
        return s


def hex_to_bin(num, fill=None):
    # convert 16-> 2
    # and fill out '0' for make [fill]bit
    ten = int(num, 16)
    return ten_to_bin(ten, fill)


################################################
# Function: main
#
# Parameters:
#   argc: the number of argument
#   argv[]: the array of a string argument
#
# Return:
#   return success exit value
#
# Info:
#   The typical main function in Python language.
#   It reads system arguments from terminal (or commands)
#   and parse an assembly file(*.s)
#   Then, it converts a certain instruction into
#   object code which is basically binary code
################################################


if __name__ == '__main__':
    argc = len(sys.argv)
    log(1, f"Arguments count: {argc}")

    if argc != 2:
        log(3, f"Usage   : {sys.argv[0]} <*.s>")
        log(3, f"Example : {sys.argv[0]} sample_input/example.s")
        exit(1)

    # Read the input file
    input_filename = sys.argv[1]
    input_filePath = os.path.join(os.curdir, input_filename)

    if os.path.exists(input_filePath) == False:
        log(3,
            f"No input file {input_filename} exists. Please check the file name and path.")
        exit(1)

    f_in = open(input_filePath, 'r')

    if f_in == None:
        log(3,
            f"Input file {input_filename} is not opened. Please check the file")
        exit(1)

    # Create the output file (*.o)
    output_filename = change_file_ext(sys.argv[1])
    output_filePath = os.path.join(os.curdir, output_filename)

    if os.path.exists(output_filePath) == True:
        log(0, f"Output file {output_filename} exists. Remake the file")
        os.remove(output_filePath)
    else:
        log(0, f"Output file {output_filename} does not exist. Make the file")

    f_out = open(output_filePath, 'w')
    if f_out == None:
        log(3,
            f"Output file {output_filename} is not opened. Please check the file")
        exit(1)

    ################################################
    # Let's compelte the below functions!
    #
    #   make_symbol_table(input)
    #   make_binary_file(output)
    ################################################
    data_seg, text_seg, data_add_dict, text_add_dict = make_symbol_table(f_in)
    
    ################################################
    # At first please make below line as a comments, or it causes error
    ################################################
    make_binary_file(f_out, data_seg, text_seg, data_add_dict, text_add_dict)

    f_in.close()
    f_out.close()
