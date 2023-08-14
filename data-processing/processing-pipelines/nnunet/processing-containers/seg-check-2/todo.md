1) Collect SEG, RTSTRUCT
2) NIFTI convert
3) Get REF image
4) NIFTI convert
5) Sort REF - to gt images
6) Collect all labels and generate master labels-list
9) Check overlap for each GT-NIFTI of each REF image - combine masks into single GT NIFTI

CONFIGURATION
- Equivalent Labels
- Merge Labels
- Policy multiple GTs
- Overlap strategy
  - skip
  - small over big
  - overlap == background


