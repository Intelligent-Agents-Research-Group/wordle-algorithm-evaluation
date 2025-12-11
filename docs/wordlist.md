# Wordle Word List

## Overview

This word list contains 5,629 five-letter English words, organized by frequency and commonality. The list is designed for use in Wordle-style word games.

## Generation Process

The word list was generated using the following process:

1. **Source Data**: The top 50,000 most common English words were extracted using the `wordfreq` library
2. **Filtering**: Words were filtered to include only:
   - Exactly 5 letters in length
   - Alphabetic characters only (no numbers or special characters)
3. **Frequency Analysis**: Each word was scored using Zipf frequency
4. **Tiering**: Words were categorized into 4 tiers based on their frequency scores
5. **Sorting**: Within each tier, words were sorted by descending frequency (most common first)

## Tier System

Words are categorized into 4 tiers based on their **Zipf frequency score**:

### What is Zipf Frequency?

Zipf frequency is a logarithmic scale that measures how commonly a word appears in natural language:
- **7+**: The most common words in the language (e.g., "the", "and", "is")
- **6.0**: Very common words, used multiple times per day
- **5.0**: Common words, used regularly
- **4.0**: Fairly common words, most people use regularly
- **3.0**: Known by most speakers, but less frequently used
- **2.0**: Somewhat obscure words
- **1.0**: Very rare words
- **0.0**: Extremely rare or specialized words

### Tier Definitions

- **Tier 1** (Zipf ≥ 4.0): Very common words that most English speakers use regularly
- **Tier 2** (Zipf ≥ 3.0): Common words that are well-known but used less frequently
- **Tier 3** (Zipf ≥ 2.5): Less common words that are still familiar to most speakers
- **Tier 4** (Zipf < 2.5): Uncommon or obscure words

## Files

- **tiered_wordlist.txt**: Complete word list with tier headers and metadata
- **wordlist.txt**: Plain word list without headers (one word per line)

## Library Used

The word list was generated using the [wordfreq](https://github.com/rspeer/wordfreq) Python library, which provides word frequencies based on a diverse corpus of text from web sources, subtitles, and other sources in multiple languages.

## Use Cases

This tiered structure is useful for:
- Implementing difficulty levels in word games
- Selecting appropriate words for different skill levels
- Training language models with frequency-aware word sets
- Educational tools that need vocabulary appropriate for different proficiency levels
