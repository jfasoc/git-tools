# Git Object Sizes in `git-pack-stats`

This document explains how `git-pack-stats` calculates the different object sizes displayed in its output.

## Packed Objects

For objects stored in `.pack` files, the statistics are derived using the `git verify-pack -v` command.

### Compressed Size
The compressed size shown for a pack file is the actual size of the `.pack` file on disk. This includes the pack header, object headers, compressed object data, and the pack trailer.

### Uncompressed Size
The uncompressed size is calculated by parsing the output of `git verify-pack -v <pack_path>`.
- The command lists each object in the pack with several columns of data.
- The **third column** in this output represents the uncompressed size of the object.
- For non-delta objects, this is their full size.
- For delta objects, this is the size of the delta data itself.
- `git-pack-stats` sums these values for all objects in the pack.

### Actual Size
Calculating the actual full uncompressed size of all objects can be a slow operation. Therefore, it is only performed when the `--actual-size` flag is used.
- When requested, `git-pack-stats` uses `git cat-file --batch-check='%(objectsize)'` to retrieve the full size of every object in the pack.
- This represents the total size the objects would occupy if they were not stored as deltas.

### Deltas
The number of delta objects in the pack is counted by parsing the output of `git verify-pack -v`. Objects with more than 5 columns in the output are identified as deltas.

### Compression % (Comp %)
The compression percentage relative to the delta-compressed data:
```
(Compressed Size / Uncompressed Size) * 100
```

### Actual Compression % (Act %)
The compression percentage relative to the full uncompressed data (only available with `--actual-size`):
```
(Compressed Size / Actual Size) * 100
```
This provides a measure of the total space saved by both delta compression and zlib compression.

---

## Loose Objects

For loose objects (stored individually in `.git/objects/??/`), the statistics are obtained using different methods.

### Compressed Size
The compressed size for loose objects is the **sum of the actual sizes of the loose object files** in `.git/objects/??/`.
- Unlike `git count-objects`, which reports "size on disk" (including filesystem block overhead), `git-pack-stats` manually walks the objects directory and uses `os.path.getsize()` on each file.
- This provides a more accurate representation of the actual compressed data stored, independent of the underlying filesystem's block size.

### Uncompressed Size
Calculating the uncompressed size of loose objects can be a slow operation in repositories with many objects. Therefore, it is only performed when the `--loose-uncompressed` flag is used.

When requested, `git-pack-stats` performs the following steps:
1.  Lists all files in the `.git/objects/` directory that match the loose object naming pattern (two-character subdirectories with 38-character filenames).
2.  Passes the resulting list of object SHAs to `git cat-file --batch-check='%(objectsize)'`.
3.  This command efficiently retrieves the uncompressed size of each object without needing to extract the full object content.
4.  The results are summed to provide the total uncompressed size for all loose objects.

If the `--loose-uncompressed` flag is not used, the "Uncompressed" and "Comp %" columns for loose objects will show "N/A".

---

## Formatting

### Human-Readable Formatting (`-H` or `--human`)
When enabled, sizes are formatted into the most appropriate unit:
- **B**: Bytes (for sizes < 1024 B)
- **KiB**: Kibibytes (for sizes < 1 MiB)
- **MiB**: Mebibytes (for sizes >= 1 MiB)

### Default Formatting
By default, sizes are displayed in raw bytes with a dot ('.') as the thousands separator for better readability (e.g., `1.048.576` bytes instead of `1048576`).
