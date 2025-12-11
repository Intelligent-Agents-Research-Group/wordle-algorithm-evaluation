from wordfreq import top_n_list, zipf_frequency

WORD_LEN = 5

def get_tier(zipf):
    if zipf >= 4.0:
        return 1
    elif zipf >= 3.0:
        return 2
    elif zipf >= 2.5:
        return 3
    else:
        return 4

def main():
    vocab = top_n_list("en", 50000)

    tiers = {1: [], 2: [], 3: [], 4: []}

    for w in vocab:
        if len(w) != WORD_LEN or not w.isalpha():
            continue
        z = zipf_frequency(w, "en")
        tier = get_tier(z)
        tiers[tier].append((w, z))

    # Sort each tier by descending frequency
    for t in tiers:
        tiers[t].sort(key=lambda x: -x[1])

    total = sum(len(tiers[t]) for t in tiers)

    with open("tiered_wordlist.txt", "w", encoding="utf-8") as f:
        f.write(f"# Total words: {total}\n\n")
        for t in [1, 2, 3, 4]:
            f.write(f"# Tier {t}\n")
            for w, _ in tiers[t]:
                f.write(w + "\n")
            f.write("\n")

    print(f"Created tiered_wordlist.txt with {total} words.")

if __name__ == "__main__":
    main()