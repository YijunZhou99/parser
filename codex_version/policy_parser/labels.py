"""Current: numeric paths and Roman/alphabetic label interpretations.
Limitations: tokens alone cannot disambiguate Roman versus alphabetic labels.
TODO(B4): resolve ambiguous labels from surrounding sequences.
Acceptance: numeric/ambiguous-label and conflict tests.
"""
import re

def match_label(text):
    return re.match(r'^(\d+(?:\.\d+)*[.)]?|\([A-Za-z0-9]+\)|[A-Za-z]+[.)])\s+(.+)$', text, re.S)


def label_grammar(label):
    return 'ambiguous' if re.search(r'[A-Za-z]', label) else 'numeric_or_raw'


def numeric_depth(label):
    token = label.strip('().')
    return len(token.split('.')) if re.fullmatch(r'\d+(?:\.\d+)*', token) else None


def roman_value(token):
    token = token.upper()
    if not token or not re.fullmatch(r'M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})', token):
        return None
    values = {'I':1, 'V':5, 'X':10, 'L':50, 'C':100, 'D':500, 'M':1000}
    return sum(-values[c] if i+1<len(token) and values[c]<values[token[i+1]] else values[c]
               for i,c in enumerate(token))


def interpretations(label):
    if not label: return []
    token = label.strip('().')
    delimiter = 'parenthesized' if label.startswith('(') else label[-1:] if label[-1:] in '.)' else 'bare'
    case = 'upper' if token.isupper() else 'lower'
    if re.fullmatch(r'\d+(?:\.\d+)*', token):
        path = [int(x) for x in token.split('.')]
        return [{'family':'numeric', 'value':path[-1], 'path':path,
                 'series':f'numeric:{delimiter}:{path[:-1]}'}]
    options = []
    if len(token)==1 and token.isascii() and token.isalpha():
        options.append({'family':'alpha','value':ord(token.lower())-ord('a')+1,
                        'series':f'alpha:{case}:{delimiter}'})
    value = roman_value(token)
    if value is not None:
        options.append({'family':'roman','value':value,'series':f'roman:{case}:{delimiter}'})
    return options
