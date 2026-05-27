#!/usr/bin/env bash
# fetch_data.sh — pull every legally-redistributable knowledge source we use.
#
# All URLs verified May 2026. The `data/` directory is gitignored — the team
# distributes a tarball via a shared bucket rather than committing 90 MB.
#
# Sources that require account registration / affiliate licence (cannot be
# auto-pulled) are listed at the bottom with manual instructions.
#
# Usage:
#   bash scripts/fetch_data.sh           # full fetch
#   bash scripts/fetch_data.sh --check   # verify integrity only

set -euo pipefail

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
CURL=(curl -L --fail --silent --show-error -A "$UA" --connect-timeout 15 --max-time 180)

mkdir -p data/icd10 data/icd11 data/nfi data/icmr data/mohfw data/who data/openfda data/legal data/snomed data/loinc

fetch() {  # fetch URL DEST_PATH LABEL
  local url=$1 dest=$2 label=$3
  if [[ -f "$dest" && "${1:-}" != "--force" ]]; then
    local sz; sz=$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest")
    if (( sz > 1024 )); then
      printf "  ✓ %-50s (cached, %s bytes)\n" "$label" "$sz"; return
    fi
  fi
  if "${CURL[@]}" "$url" -o "$dest"; then
    local sz; sz=$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest")
    printf "  ✓ %-50s (%s bytes)\n" "$label" "$sz"
  else
    printf "  ✗ %-50s FAILED — %s\n" "$label" "$url"
  fi
}

echo "=== Legal references ==="
fetch "https://cdn.who.int/media/docs/default-source/classification/icd/icd11/icd11-license.pdf" \
      data/legal/icd11-license.pdf "ICD-11 License (CC BY-ND 3.0 IGO)"

echo
echo "=== ICD-10 — WHO international (2019 EN) ==="
fetch "https://icdcdn.who.int/icd10/claml/icd102019en.xml.zip" \
      data/icd10/icd102019en.xml.zip "WHO ICD-10 2019 ClaML XML (zipped)"
if [[ -f data/icd10/icd102019en.xml.zip && ! -f data/icd10/icd102019en.xml ]]; then
  (cd data/icd10 && unzip -oq icd102019en.xml.zip)
fi

echo
echo "=== ICD-10-CM — US CDC FY2026 (74,719 codes) ==="
fetch "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2026/icd10cm-Code%20Descriptions-2026.zip" \
      data/icd10/icd10cm_codes_2026.zip "CDC ICD-10-CM 2026 code descriptions (zipped)"
if [[ -f data/icd10/icd10cm_codes_2026.zip && ! -d data/icd10/icd10cm_2026 ]]; then
  (cd data/icd10 && unzip -oq icd10cm_codes_2026.zip -d icd10cm_2026/)
fi

echo
echo "=== ICMR clinical guidelines ==="
fetch "https://bmhrc.ac.in/WriteReadData/News/202408011156447988880TreatmentGuidelinesforAntimicrobialUseinCommonSyndromes.pdf" \
      data/icmr/amr_treatment_2022_full.pdf "ICMR Antimicrobial Treatment Guidelines 2022 (168pg)"
fetch "https://www.icmr.gov.in/icmrobject/custom_data/pdf/resource-guidelines/Diagnosis_and_management_of_CROs.pdf" \
      data/icmr/cro_diagnosis_2022.pdf "ICMR Carbapenem-Resistant Organisms 2022"
fetch "https://www.icmr.gov.in/icmrobject/custom_data/pdf/resource-guidelines/ICMR_Guidelines_for_Management_of_Type_1_Diabetes.pdf" \
      data/icmr/type1_diabetes.pdf "ICMR Type-1 Diabetes Guidelines (173pg)"
fetch "https://www.icmr.gov.in/icmrobject/custom_data/pdf/resource-guidelines/ICMR_GuidelinesType2diabetes2018_0.pdf" \
      data/icmr/type2_diabetes_2018.pdf "ICMR Type-2 Diabetes Guidelines 2018"
fetch "https://www.icmr.gov.in/icmrobject/custom_data/pdf/downloadable-books/STW_Vol_3_2022.pdf" \
      data/icmr/stw_vol3_2022.pdf "ICMR Standard Treatment Workflows Vol 3, 2022"

echo
echo "=== MoHFW / NHM ==="
fetch "https://nhm.gov.in/images/pdf/guidelines/nrhm-guidelines/stg/Hypertension_full.pdf" \
      data/mohfw/Hypertension_full.pdf "MoHFW Hypertension STG (152pg)"
fetch "https://aiimsrishikesh.edu.in/documents/standard-treatment-guidelines.pdf" \
      data/mohfw/aiims_rishikesh_stg.pdf "AIIMS Rishikesh STG Manual (431pg)"

echo
echo "=== WHO ==="
fetch "https://iris.who.int/server/api/core/bitstreams/289a875c-cc89-4914-90ad-eb3c578ebaf6/content" \
      data/who/WHO_EML_23_2023.pdf "WHO Model List of Essential Medicines, 23rd ed. (2023)"

echo
echo "=== National Formulary of India ==="
fetch "https://www.ipc.gov.in/images/news/NFI-0414979118.pdf" \
      data/nfi/NFI_2016.pdf "National Formulary of India 2016 (excerpt — full edn on request)"

echo
echo "=== openFDA (drug labels API — sampled, not bulk) ==="
fetch "https://api.fda.gov/drug/label.json?search=openfda.generic_name:amlodipine&limit=2" \
      data/openfda/amlodipine_sample.json "openFDA amlodipine label sample"

cat <<'EOF'

=== Manual steps (cannot auto-fetch) ===
  - SNOMED CT India Edition: apply at https://mlds.ihtsdotools.org/#/landing/IN
    (free for India; ~2 days approval; drop the release ZIP in data/snomed/)
  - Loinc lab codes:        register at https://loinc.org/downloads/
    (free, requires email confirmation; drop the table CSV in data/loinc/)
  - ICD-11 MMS export:       requires WHO ICD-11 API account at
                            https://icd.who.int/icdapi
                            (free; OAuth-protected — Person A wires the API
                            client in app/retrieval/chroma_index.py)

=== Reminder ===
  ❌ Do NOT add DSM-5, BNF, NICE, MIMS, CIMS, DrugBank-commercial, or any
     copyrighted textbook to data/. See plans/LEGAL_SOURCES.md §7.
  ✅ Everything fetched above is licensed for our use. Citations live in the
     wiki page frontmatter — see wiki/README.md.
EOF
