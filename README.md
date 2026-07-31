# OpenScore String Quartets for Optical Music Recognition (OSSQ-OMR)
=================================

Fork of [OpenScore String Quartets Mirror](https://github.com/OpenScore/StringQuartets) optimized for Optical Music Recognition (OMR)

[OpenScore String Quartets Mirror](https://github.com/OpenScore/StringQuartets) is a collection of string quartets by "long 19th century" composers in MuseScore format with associated data.

**!Important NOTE!**  
To render or convert .mscx files in this repo, you **need to use MuseScore3 v3.6.2**  

## Part of the String Quartet OMR Benchmark

OSSQ is the dataset behind *"A Dataset and Benchmark for Optical Music Recognition of String Quartet Scores"* (MALer Lab, Sogang University). This repository holds the tracked MuseScore/MusicXML annotation sources; related repositories in the release:

- **[string-quartet-omr-benchmark](https://github.com/MALerLab/string-quartet-omr-benchmark)**: umbrella entry point for the paper and the full repository constellation.
- **[ossq-omr](https://github.com/MALerLab/ossq-omr)**: the OSSQ dataset — MuseScore/MusicXML annotation sources and their revision history. *(this repository)*
- **[omr-data-preprocessor](https://github.com/MALerLab/omr-data-preprocessor)**: the preprocessing pipeline that builds every derived symbolic format from the dataset sources.
- **[sqomr](https://github.com/MALerLab/sqomr)**: model training and evaluation experiments.
- **[lmxe](https://github.com/MALerLab/lmxe)**: the LMXE symbolic format library (derived from [OMR-Research/lmx](https://github.com/OMR-Research/lmx)).

Scores can be downloaded individually in PDF, MIDI, MusicXML, MP3 and other formats from
their [official pages][OSSQ] on MuseScore.com. Alternatively, scores can be
converted to other formats *en masse* using MuseScore's free desktop software using either
the [Batch Convert Plugin](https://musescore.org/en/project/batch-convert)
or the [command line interface](https://handbook.musescore.org/appendix/command-line-usage).


# What this repository tracks

This git repository is the **auditable revision history of the MuseScore annotation work** behind OSSQ, not a distribution channel for the full multi-format dataset. `git ls-files` tracks 878 files:

- the MuseScore/MusicXML source annotations (`sq<id>.mscx`, `sq<id>.musicxml`, `sq<id>_cleaned.musicxml`, and `sq<id>_scanned.csv` alignment data where a scanned exemplar exists)
- per-composer and per-score `README.md` files
- corpus-level metadata under [`data/`](./data/) (`.tsv`/`.yaml`)
- per-score image-segmentation metadata (`sq<id>_yolo_infos.yaml`)

All *derived* symbolic formats are intentionally gitignored, since they are large, and fully reproducible from the tracked sources:

```
scores/*/*/abc/
scores/*/*/krn/
scores/*/*/lmxe/
scores/*/*/musicxml/    # segmented systemwise/partwise MusicXML; not the top-level sq<id>.musicxml
scores/*/*/metadata/
versions/               # entire directory: packaged builds of past dataset versions
```

The bulk derived artifacts — rendered PDFs/images and the symbolic formats (`.lmxe`/`.plmxe`/`.rlmxe`, `.krn`/`.ekrn`, `.abc`/`.eabc`) — are published separately:

- **Zenodo** (versioned DOI): <!-- TODO: Zenodo DOI --> (link TBD)
- **Hugging Face**: (link TBD)

See [Regenerating derived formats](#regenerating-derived-formats) below to build them yourself instead.

# Provenance and audit history

The git history in this repository *is* the auditable record of the annotation work: every
alignment fix, correction, and style decision applied to a score is a commit. That history
spans many divergent branches — different alignment passes, annotation-style experiments, and
release snapshots — rather than a single linear trunk, because each approach is kept
individually inspectable instead of being squashed away.

The single most useful command for tracing a score's provenance is:

```sh
git log --all --source --oneline -- <path/to/score>
```

This walks every branch in a full clone (not just the default branch — see the warning below)
and labels which branch each commit came from. See [`BRANCHES.md`](./BRANCHES.md) for the full
branch inventory, verified commit counts, and more tracing commands, including why **GitHub's
web history UI only shows the default branch** and won't give you this picture on its own.

# Regenerating derived formats

Everything under `scores/*/*/{abc,krn,lmxe,musicxml,metadata}/` is reproducible from the tracked MuseScore/MusicXML sources using the [omr-data-preprocessor](https://github.com/MALerLab/omr-data-preprocessor) pipeline (`omrdp`).

Each pipeline script sets a `BASE_DIR` pointing at a local checkout of this repository. See that repo's README for full setup and its numbered pipeline (`ossq_step_001.sh` through `ossq_step_005.sh`, plus the crawl/download steps) that in turn produces the images, LMXE/PLMXE/RLMXE, **kern/eKern and ABC/eABC formats.

# [Scores directory](./scores/)

Score and lyric files are arranged in the following directory structure:

```yaml
<composer>/
  <set>/
    sq<id>.mscx
    sq<id>.musicxml
    sq<id>_cleaned.musicxml # optional dangling backup and invisible element cleaned version
    sq<id>_synthetic.pdf
    sq<id>_scanned.pdf # optional scanned version from IMSLP
    sq<id>_scanned.csv # optional alignment data
    images/
      synthetic/
        sq<id>_yolo_infos.yaml # infos on image segmentation for reproducibility and future reference
        original/
          sq<id>:<page>.png # 4-digits page index starting from 1
        cropped/
          sq<id>:<page>:<system>.png # 4-digits page, system index starting from 1
        systemwise/
          sq<id>:<page>:<system>.png # 4-digits page, system index starting from 1
        partwise/
          sq<id>:<page>:<system>:<part>.png # 4-digits page, system index starting from 1, 1-digit part index [1,4]
      scanned/
        sq<id>_yolo_infos.yaml # infos on image segmentation for reproducibility and future reference
        original/
        cropped/
        systemwise/
        partwise/
    metadata/
      synthetic/
        systemwise/
          sq<id>:<page>:<system>.yaml # metadata for synthetic systemwise images
        partwise/
          sq<id>:<page>:<system>:<part>.yaml # metadata for synthetic partwise images
      scanned/
    lmxe/
      synthetic/
	      systemwise/
          sq<id>:<page>:<system>.lmxe
          sq<id>:<page>:<system>.plmxe # parametrized LMXE
          sq<id>:<page>:<system>.rlmxe # relative LMXE
        partwise/
          sq<id>:<page>:<system>:<part>.lmxe
          sq<id>:<page>:<system>:<part>.rlmxe # relative LMXE
      scanned/
    krn/
      synthetic/
        systemwise/
          sq<id>:<page>:<system>.krn
          sq<id>:<page>:<system>.ekrn
        partwise/
          sq<id>:<page>:<system>:<part>.ekrn
      scanned/
    abc/
      synthetic/
        systemwise/
          sq<id>:<page>:<system>.abc
          sq<id>:<page>:<system>.eabc
        partwise/
          sq<id>:<page>:<system>:<part>.abc
          sq<id>:<page>:<system>:<part>.eabc
      scanned/
    musicxml/
      synthetic/
        systemwise/
          sq<id>:<page>:<system>.musicxml
        systemwise_krn/ # musicxml file with time signatures for krn conversion
          sq<id>:<page>:<system>.musicxml
        partwise/
          sq<id>:<page>:<system>:<part>.musicxml
        partwise_krn/ # musicxml file with time signatures for krn conversion
          sq<id>:<page>:<system>:<part>.musicxml
      scanned/
        systemwise/
        systemwise_krn/
        partwise/
        partwise_krn/
```


Directories:

- `<composer>` - composer's name in the form `Last,_First_Second...`.
- `<set>` - name of the extended work that the song belongs to, if any.

The top-level `search`/`search_id`/`search_img` shell scripts are developer helpers for looking up a score's derived files by MuseScore ID during pipeline work; they aren't required to use the dataset.

## Filenames

Score files within each song directory are named as follows

```
sq<id>.mscx
```

Filename components:

- `sq` - standing for string quartets
- `<id>` - the score's unique Musescore ID
- `.mscx` - the file extension for MuseScore's uncompressed score format.

## Unicode characters in file paths

With the exception of a few unsafe or illegal characters, names of songs,
sets and composers have been left in their original forms.

Modern filesystems should have no problems with Unicode characters in
file paths. If the paths are displayed incorrectly by `git`, try setting:

```
git config core.quotePath false
```

Users on macOS may also need to set:

```
git config core.precomposeunicode true
```

__Tip:__ Add `--global` after `config` in the above commands to make `git`
behave this way by default for all repositories on your local machine.

# [Data directory](./data/)

The `Data/` directory contains the following:
- composers.tsv and composers.yaml: information about the corpus composers.
- corpus.tsv and corpus.yaml: total numbers of composers, sets, and scores.
- scores.tsv and scores.yaml: information about each score
- scores_w_url.yaml: per-score IMSLP source metadata (catalog number and direct scan URL) for each MuseScore entry.
- scores_w_pub.yaml: per-score publisher, publication date, copyright and source-type metadata.
- publication_report.md: publication and source-type analysis of the corpus.
- scanned_score_types.tsv: per-score source-type table (id, path, name, type, link, imslp, set_id).
- score_types.md: legend for the `type` codes used in that TSV.
- sets.tsv and sets.yaml: information about each set (collection of scores).
- vocabulary.txt: the symbolic-token vocabulary used across the corpus.
- code-plots/: `plot.py`, for producing the summative plots below, and their output.

## [Data plots](./data/code-plots/)

Summative plots of the corpus contents:

1. The number of corpus composers alive and active over time.
![composer_dates](./data/code-plots/composer_dates.pdf)

1. The number of works by the top, most represented composers.
![composer_scores](./data/code-plots/composer_scores.pdf)

1. The composer nationalities
![composer_nationalities](./data/code-plots/composer_nationalities.pdf)

# License and acknowledgement

These scores are released under Creative Commons Zero (CC0). See LICENSE.txt. This covers both the annotation sources tracked in this repository and the bulk-distributed derived formats.

We kindly ask that you credit OpenScore String Quartets and provide a link to [OSSQ] or this repository for any public-facing use of these scores.

# Citation

If you use the OMR benchmark (derived formats, splits, baselines), please cite the paper this dataset accompanies:

```bibtex
@inproceedings{Kim2026sqomrbench,
    title     = {A Dataset and Benchmark for Optical Music Recognition of String Quartet Scores},
    author    = {Dongmin Kim and Brian Liu and Jose J. Valero-Mas and Dasaem Jeong},
    year      = 2026,
    booktitle = {Proceedings of the 27th International Society for Music Information Retrieval Conference (ISMIR)},
}
```

If you use the underlying OpenScore String Quartet corpus itself, please also cite the original report published in DLfM 2023:

```
@inproceedings{gotham_openscore_2023,
	address = {Milan Italy},
	title = {The “{OpenScore} {String} {Quartet}” {Corpus}},
	copyright = {All rights reserved},
	isbn = {9798400708336},
	url = {https://dl.acm.org/doi/10.1145/3625135.3625155},
	doi = {10.1145/3625135.3625155},
	language = {en},
	urldate = {2023-11-16},
	booktitle = {Proceedings of the 10th {International} {Conference} on {Digital} {Libraries} for {Musicology}},
	publisher = {ACM},
	author = {Gotham, Mark R. H. and Redbond, Maureen and Bower, Bruno and Jonas, Peter},
	month = nov,
	year = {2023},
	pages = {49--57},
}
```
