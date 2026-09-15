// The shell seeds localStorage["settings"] with the settings shared by all
// views before this one loads. These defaults only cover the case where it has
// not done so, and therefore hold no more than the single setting this view
// reads: the fields the dataset dashboard groups its histograms by.
export const settings = {
  landingPage: ['Patient Sex', 'Modality'],
}
