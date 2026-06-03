import type { QueryNode } from '@/types/domain'

/**
 * Curated example queries surfaced behind the "Examples" button. Field paths
 * follow the shipped `dicom-series` schema (DICOM keys use the
 * `<tag> <Keyword>_<type>` convention) and the dataset model (`dataset` key +
 * `contains` links). Body-part presence depends on the source data, but the
 * path/convention is correct regardless.
 */
export interface QueryExample {
  label: string
  description: string
  node: QueryNode
}

export const QUERY_EXAMPLES: QueryExample[] = [
  {
    label: 'Only segmentations',
    description: 'DICOM series whose modality is SEG.',
    node: {
      type: 'filter',
      field: 'metadata.dicom-series.00080060 Modality_keyword',
      op: 'eq',
      value: 'SEG',
    },
  },
  {
    label: 'Abdomen CTs not in a dataset',
    description: 'CT series of the abdomen that are not a member of any dataset.',
    node: {
      type: 'group',
      op: 'and',
      children: [
        {
          type: 'filter',
          field: 'metadata.dicom-series.00080060 Modality_keyword',
          op: 'eq',
          value: 'CT',
        },
        {
          type: 'filter',
          field: 'metadata.dicom-series.00180015 BodyPartExamined_keyword',
          op: 'eq',
          value: 'ABDOMEN',
        },
        {
          type: 'filter',
          field: 'links',
          op: 'no_incoming_link',
          value: { link_type: 'contains' },
        },
      ],
    },
  },
  {
    label: 'All datasets',
    description: 'Every entity that is a dataset.',
    node: {
      type: 'filter',
      field: 'metadata.dataset',
      op: 'has_key',
    },
  },
  {
    label: 'Entities not in any dataset',
    description: 'Entities with no parent dataset (no incoming contains link).',
    node: {
      type: 'filter',
      field: 'links',
      op: 'no_incoming_link',
      value: { link_type: 'contains' },
    },
  },
]
