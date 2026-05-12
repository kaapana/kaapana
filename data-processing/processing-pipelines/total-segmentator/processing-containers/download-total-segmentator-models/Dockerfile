FROM local-only/base-python-cpu:latest
LABEL IMAGE="download-total-segmentator-models"
LABEL VERSION="0.1.2"
LABEL BUILD_IGNORE="False"

# where we temporarily store the weights *inside the image*
ENV TOTALSEG_PARENT=/opt/weights/total_segmentator

# ---- tools + download + unzip (build‑time) --------------------------------
RUN set -eux; \
    TDIR="$TOTALSEG_PARENT/nnUNet/3d_fullres"; \
    mkdir -p "$TDIR"; \
    cd "$TDIR"; \
    for URL in \
      "https://zenodo.org/record/6802342/files/Task251_TotalSegmentator_part1_organs_1139subj.zip?download=1" \
      "https://zenodo.org/record/6802358/files/Task252_TotalSegmentator_part2_vertebrae_1139subj.zip?download=1" \
      "https://zenodo.org/record/6802360/files/Task253_TotalSegmentator_part3_cardiac_1139subj.zip?download=1" \
      "https://zenodo.org/record/6802366/files/Task254_TotalSegmentator_part4_muscles_1139subj.zip?download=1" \
      "https://zenodo.org/record/6802452/files/Task255_TotalSegmentator_part5_ribs_1139subj.zip?download=1" \
      "https://zenodo.org/record/6802052/files/Task256_TotalSegmentator_3mm_1139subj.zip?download=1" \
      "https://zenodo.org/record/7064718/files/Task258_lung_vessels_248subj.zip?download=1" \
      "https://zenodo.org/record/7079161/files/Task150_icb_v0.zip?download=1" \
      "https://zenodo.org/record/7234263/files/Task260_hip_implant_71subj.zip?download=1" \
      "https://zenodo.org/record/7334272/files/Task269_Body_extrem_6mm_1200subj.zip?download=1" \
      "https://zenodo.org/record/7271576/files/Task503_cardiac_motion.zip?download=1" \
      "https://zenodo.org/record/7510286/files/Task273_Body_extrem_1259subj.zip?download=1" \
      "https://zenodo.org/record/7510288/files/Task315_thoraxCT.zip?download=1" \
      "https://zenodo.org/record/7573746/files/Task008_HepaticVessel.zip?download=1"; \
      do \
        ZIP=$(basename "${URL%%\?*}"); \
        DIR="${ZIP%.zip}"; \
        if [ -d "$DIR" ]; then echo "skip $DIR"; continue; fi; \
        echo "↓ $ZIP"; \
        wget -q --show-progress -O "$ZIP" "$URL"; \
        unzip -q "$ZIP"; \
        rm "$ZIP"; \
    done
# ---- runtime: copy into the PVC if it is still empty ----------------------
ENTRYPOINT ["/bin/sh","-c","set -e; \
  dst=/models/total_segmentator; \
  echo 'Copying Total-Segmentator weights into PVC…'; \
  mkdir -p \"$dst\"; \
  cp -r /opt/weights/* /models/; \
  echo '✓ done'; \
  "]
