"""Narration for America After Dark (Oct. 2026): the White House and Lincoln's ghost, Eastern State Penitentiary, and
the Stanley Hotel. Every sighting is worded as reported / said to / legend.

python3 afterdark_us_vo.py [NAME ...]  ->  shorts/r_<name>/vo.wav (24 kHz) and vo.json  (same method as reels_vo.py)
"""
import sys

import reels_vo as V

V.SAY += [(r"\bWilhelmina\b", "Vil-hel-mee-nuh"), (r"\bEstes\b", "Es-tiss"), (r"\bFreelan\b", "Free-lan"),
          (r"\b1865\b", "eighteen sixty-five"), (r"\b1942\b", "nineteen forty-two"),
          (r"\b1829\b", "eighteen twenty-nine"), (r"\b1842\b", "eighteen forty-two"),
          (r"\b1929\b", "nineteen twenty-nine"), (r"\b1970\b", "nineteen seventy"),
          (r"\b1971\b", "nineteen seventy-one"), (r"\b1909\b", "nineteen-oh-nine"),
          (r"\b1974\b", "nineteen seventy-four"), (r"\b1977\b", "nineteen seventy-seven"),
          (r"\b1911\b", "nineteen eleven"), (r"\b217\b", "two seventeen")]

V.REELS.update({
    "wh_lincoln": [
        ("The most famous ghost at the White House is said to be Abraham Lincoln.", 0.4),
        ("Since his assassination in 1865, staff and guests have reported seeing him.", 0.35),
        ("First Lady Grace Coolidge said she saw him at a window in the Yellow Oval Room.", 0.35),
        ("In 1942, Queen Wilhelmina of the Netherlands reportedly saw him at her door. "
         "Accounts differ on whether she fainted.", 0.35),
        ("Others reported knocks at the Lincoln Bedroom door. In Lincoln's day, it was his office.", 0.35),
        ("Some of the legend may trace to Jerry Smith, a longtime servant who told ghost stories to reporters.", 0.4),
        ("No one has proved any of it.", 0.4),
        ("Follow for more America After Dark.", 0.0),
    ],
    "eastern_state": [
        ("Is Eastern State Penitentiary haunted? Its own audio tour says: who knows?", 0.4),
        ("It opened in Philadelphia in 1829, built around solitary confinement.", 0.35),
        ("Charles Dickens visited in 1842 and called the practice cruel and wrong.", 0.35),
        ("Al Capone served time here in 1929. Tradition names one cell as his, but the site can't be sure.", 0.35),
        ("Pennsylvania stopped running it in 1970. The city used it briefly in 1971.", 0.35),
        ("Visitors have said they sensed something. A locksmith once told an author of a powerful energy at an "
         "old cell.", 0.4),
        ("None of it is proven.", 0.4),
        ("Follow for more America After Dark.", 0.0),
    ],
    "stanley": [
        ("This Colorado hotel inspired Stephen King's The Shining.", 0.4),
        ("The steam-car maker Freelan Stanley opened it in Estes Park in 1909.", 0.35),
        ("In 1974, Stephen King and his wife spent a night here.", 0.3),
        ("Room 217 is said to be where he stayed. The novel came out in 1977.", 0.35),
        ("In June 1911, a gas explosion injured a maid. Newspapers differed on her name and the details.", 0.35),
        ("The hotel's legend names her Elizabeth Wilson, and says her spirit still tidies rooms.", 0.4),
        ("It's a reported haunting. It has never been proved.", 0.4),
        ("Follow for more America After Dark.", 0.0),
    ],
})
if __name__ == "__main__":
    V.main(sys.argv[1:] or ["wh_lincoln", "eastern_state", "stanley"])

