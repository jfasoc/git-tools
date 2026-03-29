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
- `git-pack-stats` sums these values for all objects in the pack (commits, trees, blobs, and tags).

### Compression %
The compression percentage for a pack is calculated as:
```
(Compressed Size / Uncompressed Size) * 100
```
This represents the size of the packed data relative to its original, uncompressed state. A lower percentage indicates better compression.

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
