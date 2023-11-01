font = r"""
┌───────┐  ┌───────┐  ┌───────┐  ┌─────┐    ┌────────  ┌────────  ┌───────┐
├───────┤  ├───────┤  |          |     └─┐  ├───────   ├───────   |    ───┐
|       |  └───────┘  └───────┘  └───────┘  └────────  |          └───────┘

|       |     ─┬─         ─┬─    |      /   |          ┌───┬───┐  ┌───────┐
├───────┤      |           |     ├─────┤    |          |   |   |  |       |
|       |     ─└─        ──┘     |      \   └────────  |   |   |  |       |

┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐  ┌───┬───┐  |       |
|       |  ├───────┘  |       |  ├─────┬─┘  └───────┐      |      |       |
└───────┘  |          └─────┤─┘  |      \   └───────┘      |      └───────┘

|       |  |   |   |  \       /  |       |  ────────┐
|     ┌─┘  |   |   |   ├─────┤   └───┬───┘  ┌───────┘
└─────┘    └───└───┘  /       \      |      └────────"""
letterwidth = 9
letterheight = 3
spacingwidth = 2

lettersize = letterwidth * letterheight + spacingwidth * letterheight

font = [
    [line[i : i + letterwidth] for i in range(0, len(line), letterwidth + spacingwidth)] for line in font.split("\n") if line
]

def niter(t, n: int):
    a = iter(t)
    try:
        while True:
            yield [next(a) for _ in range(n)]
    except StopIteration:
        return

font = [[lines[j][i] for j in range(letterheight)] for lines in niter(font, letterheight) for i in range(len(lines[0]))]

alphabet = "abcdefghijklmnopqrstuvwxyz"
fontd = {a: font[i] for i, a in enumerate(alphabet)}

if not " " in fontd:
    fontd[" "] = [" " * letterwidth] * letterheight
fontd["\n"] = fontd[" "]


def fontify(text: str):
    if not text:
        raise ValueError("Where text??")
    if len(text) > 1800 / lettersize:
        raise ValueError("Text too long")
    if any((x not in fontd for x in text)):
        inv = "', '".join((x for x in text if not x in fontd))
        raise ValueError(f"Invalid characters: '{inv}'")
    out = ""
    for line in text.split("\n"):
        for y in range(letterheight):
            out += "".join((fontd[c][y] for c in line)) + "\n"
        out += "\n"
    return f"```\n{out[:-2]}```"


print(fontify("hello\n\nthere"))
