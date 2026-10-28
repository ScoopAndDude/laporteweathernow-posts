"""Narration for La Porte After Dark (Oct. 2026): Belle Gunness Parts 7 and 8, and the 1933 prison break.

python3 afterdark_vo.py [NAME ...]  ->  shorts/r_<name>/vo.wav (24 kHz) and vo.json  (same method as reels_vo.py)
"""
import sys

import reels_vo as V

V.SAY += [(r"\bLamphere\b", "Lam-fear"), (r"\bSarber\b", "Sar-ber"), (r"\b1907\b", "nineteen-oh-seven"),
          (r"\b1909\b", "nineteen-oh-nine"), (r"\b1910\b", "nineteen-ten"), (r"\b1933\b", "nineteen thirty-three"),
          (r"\bE\. A\.", "E. A.")]

V.REELS.update({
    "belle8": [
        ("Was Belle Gunness living in Los Angeles in 1931?", 0.35),
        ("August Lindstrom died there in February. His housekeeper, Esther Carlson, and a neighbor were "
         "charged with poisoning him.", 0.3),
        ("Chemists said there was poison enough to kill ten men.", 0.3),
        ("Word spread that Carlson might be Belle. People who knew Belle were brought to see her.", 0.3),
        ("But Carlson had tuberculosis, and died before her trial.", 0.3),
        ("Asked if she poisoned him, she mumbled something that might have been yes.", 0.3),
        ("The papers disagreed. One said friends denied it. Another said two men were positive.", 0.3),
        ("The neighbor was acquitted. Whether Carlson was Belle has never been proved.", 0.4),
        ("Follow for more La Porte After Dark.", 0.0),
    ],
    "belle7": [
        ("Only one man was ever convicted in the Belle Gunness case.", 0.4),
        ("Ray Lamphere worked her farm from August 1907, until she fired him in February 1908.", 0.35),
        ("After the April fire, he went on trial. A jury found him guilty of arson, but not murder.", 0.35),
        ("He died in custody on December thirtieth, 1909.", 0.4),
        ("Weeks later, a minister made public a confession Lamphere had given him.", 0.4),
        ("One newspaper said he admitted killing four people, but denied setting the fire.", 0.35),
        ("Other accounts said he helped bury victims, and that Belle escaped alive.", 0.4),
        ("The records don't agree.", 0.4),
        ("Follow for more La Porte After Dark.", 0.0),
    ],
    "break33": [
        ("Ten men. Three pistols. Dillinger wasn't even there.", 0.35),
        ("On September twenty-sixth, 1933, ten inmates escaped the Indiana State Prison in Michigan City.", 0.35),
        ("They used three pistols that John Dillinger had smuggled in.", 0.4),
        ("But he'd been paroled that May, and was arrested in Dayton, Ohio on September twenty-second.", 0.4),
        ("Harry Pierpont and Charles Makley were among the ten. On October twelfth, they freed Dillinger from "
         "jail in Lima, Ohio. Sheriff Jess Sarber was killed.", 0.45),
        ("How did the guns get in? No one knows for sure. The most believed theory: boxes of thread for the shirt "
         "factory.", 0.4),
        ("Follow for more La Porte After Dark.", 0.0),
    ],
})
if __name__ == "__main__":
    V.main(sys.argv[1:] or ["belle8", "belle7", "break33"])
