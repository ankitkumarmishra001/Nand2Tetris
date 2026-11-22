import re
import sys

COMP = {
    '0': '0101010', '1': '0111111', '-1': '0111010',
    'D': '0001100', 'A': '0110000', '!D': '0001101', '!A': '0110001',
    '-D': '0001111', '-A': '0110011', 'D+1': '0011111', 'A+1': '0110111',
    'D-1': '0001110', 'A-1': '0110010', 'D+A': '0000010', 'D-A': '0010011',
    'A-D': '0000111', 'D&A': '0000000', 'D|A': '0010101',
    'M': '1110000', '!M': '1110001', '-M': '1110011', 'M+1': '1110111',
    'M-1': '1110010', 'D+M': '1000010', 'D-M': '1010011', 'M-D': '1000111',
    'D&M': '1000000', 'D|M': '1010101',
}

JUMP = {
    '': '000', 'JGT': '001', 'JEQ': '010', 'JGE': '011',
    'JLT': '100', 'JNE': '101', 'JLE': '110', 'JMP': '111',
}

NAME_RE = re.compile(r'^[A-Za-z_.$:][A-Za-z0-9_.$:]*$')


def predefined_symbols():
    symbols = {'SP': 0, 'LCL': 1, 'ARG': 2, 'THIS': 3, 'THAT': 4,
               'SCREEN': 16384, 'KBD': 24576}
    for i in range(16):
        symbols['R' + str(i)] = i
    return symbols


def dest_bits(dest):
    return ('1' if 'A' in dest else '0') + \
           ('1' if 'D' in dest else '0') + \
           ('1' if 'M' in dest else '0')


def assemble_c(text):
    """Return (binary, error_message). One of them is None."""
    if text.count('=') > 1 or text.count(';') > 1:
        return None, 'invalid instruction'
    dest, jump = '', ''
    rest = text
    if '=' in rest:
        dest, rest = rest.split('=', 1)
        if dest == '' or not set(dest) <= set('ADM') or len(set(dest)) != len(dest):
            return None, 'invalid destination "' + dest + '"'
    if ';' in rest:
        comp, jump = rest.split(';', 1)
    else:
        comp = rest
    if comp not in COMP and len(comp) == 3 and comp[1] in '+&|':
        comp = comp[2] + comp[1] + comp[0]  # allow A+D as D+A
    if comp not in COMP:
        return None, 'invalid computation "' + comp + '"'
    if jump not in JUMP:
        return None, 'invalid jump "' + jump + '"'
    return '111' + COMP[comp] + dest_bits(dest) + JUMP[jump], None


def assemble(path):
    symbols = predefined_symbols()
    errors = []
    lines = []

    # Read file, remove comments, spaces and blank lines (keep real line numbers)
    with open(path) as f:
        for number, raw in enumerate(f, 1):
            text = ''.join(raw.split('//')[0].split())
            if text:
                lines.append((number, text))

    # First reading: record labels
    rom = 0
    for number, text in lines:
        if text.startswith('('):
            name = text[1:-1]
            if not text.endswith(')') or not NAME_RE.match(name):
                errors.append('Line %d: invalid label "%s"' % (number, text))
            elif name in symbols:
                errors.append('Line %d: label "%s" is already defined' % (number, name))
            else:
                symbols[name] = rom
        else:
            rom += 1

    # Second reading: translate to 16 bits
    output = []
    next_var = 16
    for number, text in lines:
        if text.startswith('('):
            continue
        if text.startswith('@'):
            sym = text[1:]
            if sym.isdigit():
                value = int(sym)
                if value > 32767:
                    errors.append('Line %d: address %d is too large' % (number, value))
                    continue
            elif NAME_RE.match(sym):
                if sym not in symbols:
                    symbols[sym] = next_var
                    next_var += 1
                value = symbols[sym]
            else:
                errors.append('Line %d: invalid A-instruction "%s"' % (number, text))
                continue
            output.append('0' + format(value, '015b'))
        else:
            binary, problem = assemble_c(text)
            if problem:
                errors.append('Line %d: %s' % (number, problem))
            else:
                output.append(binary)

    return output, errors


def main():
    if len(sys.argv) != 2 or not sys.argv[1].endswith('.asm'):
        print('Usage: python assembler.py <file.asm>')
        return
    path = sys.argv[1]
    try:
        output, errors = assemble(path)
    except FileNotFoundError:
        print('Error: file "%s" not found' % path)
        return
    if errors:
        for message in errors:
            print(message)
        print('Assembly failed: %d error(s). No .hack file written.' % len(errors))
        return
    out_path = path[:-4] + '.hack'
    with open(out_path, 'w') as f:
        f.write('\n'.join(output) + '\n')
    print('Wrote %s (%d instructions)' % (out_path, len(output)))


main()