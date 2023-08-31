/*---------------------------------------------------------------
*  Copyright 2015 by the Radiological Society of North America
*
*  This source software is released under the terms of the
*  RSNA Public License (http://mirc.rsna.org/rsnapubliclicense.pdf)
*----------------------------------------------------------------*/

package org.rsna.ctp.stdstages.dicom;

import org.apache.log4j.*;
import org.dcm4che.dict.*;

import java.util.*;

public class PCTable extends Hashtable<String,LinkedList<String>> {

    final static Logger logger = Logger.getLogger(PCTable.class);

	static SkipTable skipTable = new SkipTable();
	
	private static PCTable pcTable = null;

	public static synchronized PCTable getInstance() {
		if (pcTable == null) {
			pcTable = new PCTable();
		}
		return pcTable;
	}

	protected PCTable() {
		super();
		for (int i=0; i<pcs.length; i++) {
			this.put(pcs[i].asUID, pcs[i].list);
		}
		for (int i=0; i<ext_pcs.length; i++) {
			this.put(ext_pcs[i].asUID, ext_pcs[i].list);
		}
	}

	protected PCTable(boolean skip) {
		super();
		for (int i=0; i<pcs.length; i++) {
			if (skip) {
				for (String ts : skipTable) {
					pcs[i].list.remove(ts);
				}
			}
			this.put(pcs[i].asUID, pcs[i].list);
		}
		//Accept everything in the ext table, even if skipping.
		for (int i=0; i<ext_pcs.length; i++) {
			this.put(ext_pcs[i].asUID, ext_pcs[i].list);
		}
	}

	protected PCTable(LinkedList<String> sopClasses) {
		super();
		getInstance();
		for (String sopClass : sopClasses) {
			if (!sopClass.contains(".")) sopClass = UIDs.forName(sopClass);
			LinkedList<String> pcList = pcTable.get(sopClass);
			if (pcList != null) this.put(sopClass, pcList);
		}
		logger.debug("PCTable.size: "+this.size());
	}

	public static synchronized PCTable getInstance(LinkedList<String> sopClasses) {
		if ((sopClasses != null) && (sopClasses.size() > 0)) {
			return new PCTable(sopClasses);
		}
		else return PCTable.getInstance();
	}
	
	public void removeSkippedSyntaxes() {
		for (String scUID : pcTable.keySet()) {
			LinkedList<String> tsUIDs = pcTable.get(scUID);
			for (String ts : skipTable) {
				tsUIDs.remove(ts);
			}
		}
	}

	static class PC {
		public String asUID;
		public LinkedList<String> list;

		//This method always looks up asName in the dictionary.
		public PC(String asName, String listString) {
			this.asUID = UIDs.forName(asName);
			this.list = tokenize(listString, new LinkedList<String>());
		}

		//This method is for the ext_pcs, to allow UIDs to be added that
		//are not in the dictionary. If ext is true, use asName as the UID;
		//else look it up in the dictionary.
		public PC(String asName, String listString, boolean ext) {
			this.asUID = ext ? asName : UIDs.forName(asName);
			this.list = tokenize(listString, new LinkedList<String>());
		}

		private static LinkedList<String> tokenize(String s, LinkedList<String> list) {
			StringTokenizer stk = new StringTokenizer(s, ", ");
			while (stk.hasMoreTokens()) {
				String tk = stk.nextToken();
				if (tk.equals("$ts-native")) tokenize(tsNative, list);
                else if (tk.equals("$ts-implicitleonly")) tokenize(tsImplicitLEOnly, list); // <-- Disney - 20140612
				else if (tk.equals("$ts-jpeglossless")) tokenize(tsJPEGLossless, list);
				else if (tk.equals("$ts-epd")) tokenize(tsEPD, list);
				else list.add(UIDs.forName(tk));
			}
			return list;
		}
	}

	static String tsJPEGLossless =
			"JPEGLossless,"+
			"JPEGLossless14";
	static String tsEPD =
			"$ts-jpeglossless,"+
			"JPEG2000Lossless,"+
			"JPEG2000Lossy,"+
			"JPEGExtended,"+
			"JPEGLSLossy,"+
			"RLELossless,"+
			"JPEGBaseline";
	static String tsNative =
			"ExplicitVRLittleEndian,"+
			"ImplicitVRLittleEndian";
    static String tsImplicitLEOnly =
            "ImplicitVRLittleEndian";

	static PC[] pcs = {
		new PC("AcquisitionContextSRStorage","$ts-native"),
		//new PC("AgfaAttributePresentationState","$ts-native"),
		new PC("AmbulatoryECGWaveformStorage","$ts-native"),
		new PC("AmbulatoryECGWaveformStorage","$ts-native"),
		new PC("ArterialPulseWaveformStorage","$ts-native"),
		new PC("BasicStudyContentNotification","$ts-native"),
		new PC("BasicTextSR","$ts-native"),
		new PC("BasicVoiceAudioWaveformStorage","$ts-native"),
		new PC("BlendingSoftcopyPresentationStateStorage","$ts-native"),
		new PC("BreastTomosynthesisImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("CardiacElectrophysiologyWaveformStorage","$ts-native"),
		new PC("ChestCADSR","$ts-native"),
		new PC("ColonCADSR","$ts-native"),
		new PC("ColorSoftcopyPresentationStateStorage","$ts-native"),
		new PC("ComprehensiveSR","$ts-native"),
		new PC("Comprehensive3DSRStorage","$ts-native"),
		new PC("ComputedRadiographyImageStorage","$ts-epd,$ts-native"),
		new PC("CTImageStorage","$ts-epd,$ts-native"),
		//new PC("Dcm4cheEncapsulatedDocumentStorage","$ts-native"),
		//new PC("Dcm4cheStudyInfo","$ts-native"),
		//new PC("Dcm4cheUpgradedCTImageStorage","$ts-epd,$ts-native"),
		//new PC("Dcm4cheUpgradedMRImageStorage","$ts-epd,$ts-native"),
		//new PC("Dcm4cheUpgradedPETImageStorage","$ts-epd,$ts-native"),
		new PC("DeformableSpatialRegistrationStorage","$ts-native"),
		new PC("DigitalIntraoralXRayImageStorageForPresentation","$ts-jpeglossless,$ts-native"),
		new PC("DigitalIntraoralXRayImageStorageForProcessing","$ts-jpeglossless,$ts-native"),
		new PC("DigitalMammographyXRayImageStorageForPresentation","$ts-jpeglossless,$ts-native"),
		new PC("DigitalMammographyXRayImageStorageForProcessing","$ts-jpeglossless,$ts-native"),
		new PC("DigitalXRayImageStorageForPresentation","$ts-jpeglossless,$ts-native"),
		new PC("DigitalXRayImageStorageForProcessing","$ts-jpeglossless,$ts-native"),
		new PC("EncapsulatedCDAStorage","$ts-native"),
		new PC("EncapsulatedPDFStorage","$ts-native"),
		new PC("EnhancedCTImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("EnhancedMRColorImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("EnhancedMRImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("EnhancedPETImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("EnhancedSR","$ts-native"),
		new PC("EnhancedUSVolumeStorage","$ts-epd,$ts-native"),
		new PC("EnhancedXRayAngiographicImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("EnhancedXRayRadiofluoroscopicImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("ExtensibleSRStorage","$ts-native"),
		new PC("GeneralAudioWaveform","$ts-native"),
		new PC("GeneralECGWaveformStorage","$ts-native"),
		new PC("GrayscaleSoftcopyPresentationStateStorage","$ts-native"),
		new PC("HangingProtocolStorage","$ts-native"),
		new PC("HardcopyColorImageStorage","$ts-native"),
		new PC("HardcopyGrayscaleImageStorage","$ts-native"),
		new PC("HemodynamicWaveformStorage","$ts-native"),
		new PC("ImageOverlayBox","$ts-native"),
		new PC("ImplantationPlanSRStorage","$ts-native"),
		new PC("KeyObjectSelectionDocument","$ts-native"),
		new PC("MammographyCADSR","$ts-native"),
		new PC("MediaStorageDirectoryStorage","$ts-native"),
		new PC("MRImageStorage","$ts-epd,$ts-native"),
		new PC("MRSpectroscopyStorage","$ts-epd,$ts-native"),
		new PC("MultiframeColorSecondaryCaptureImageStorage","$ts-jpeglossless,JPEGBaseline,$ts-native"),
		new PC("MultiframeGrayscaleByteSecondaryCaptureImageStorage","$ts-jpeglossless,JPEGBaseline,$ts-native"),
		new PC("MultiframeGrayscaleWordSecondaryCaptureImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("MultiframeSingleBitSecondaryCaptureImageStorage","$ts-native"),
		new PC("MultiframeTrueColorSecondaryCaptureImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("NuclearMedicineImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("NuclearMedicineImageStorageRetired","$ts-native"),
		new PC("OphthalmicPhotography16BitImageStorage","$ts-epd,$ts-native"),
		new PC("OphthalmicPhotography8BitImageStorage","$ts-epd,$ts-native"),
		new PC("OphthalmicTomographyImageStorage","$ts-epd,$ts-native"),
		new PC("PatientRadiationDoseSRStorage","$ts-native"),
		new PC("ParametricMapStorage","$ts-native"),
		new PC("PerformedImagingAgentAdministrationSRStorage","$ts-native"),
		new PC("PlannedImagingAgentAdministrationSRStorage","$ts-native"),
		new PC("PositronEmissionTomographyImageStorage","$ts-epd,$ts-native"),
		new PC("PresentationLUT","$ts-native"),
		new PC("ProceduralEventLoggingSOPClass","$ts-native"),
		new PC("ProcedureLogStorage","$ts-native"),
		new PC("PseudoColorSoftcopyPresentationStateStorage","$ts-native"),
		new PC("RadiopharmaceuticalRadiationDoseSRStorage","$ts-native"),
		new PC("RawDataStorage","$ts-native"),
		new PC("RespiratoryWaveformStorage","$ts-native"),
		new PC("RTBeamsTreatmentRecordStorage","$ts-native"),
		new PC("RTBrachyTreatmentRecordStorage","$ts-native"),
		new PC("RTDoseStorage","$ts-native"),
		new PC("RTImageStorage","$ts-epd,$ts-native"),
		new PC("RTIonBeamsTreatmentRecordStorage","$ts-native"),
		new PC("RTIonPlanStorage","$ts-native"),
		new PC("RTPlanStorage","$ts-native"),
		new PC("RTStructureSetStorage","$ts-native") /*was $ts-implicitleonly*/,
		new PC("RTTreatmentSummaryRecordStorage","$ts-native"),
		new PC("SecondaryCaptureImageStorage","$ts-epd,$ts-native"),
		new PC("SegmentationStorage","$ts-native"),
		//new PC("SiemensCSANonImageStorage","$ts-native"),
		new PC("SimplifiedAdultEchoSRStorage","$ts-native"),
		new PC("SpatialFiducialsStorage","$ts-native"),
		new PC("SpatialRegistrationStorage","$ts-native"),
		new PC("StandaloneCurveStorage","$ts-native"),
		new PC("StandaloneModalityLUTStorage","$ts-native"),
		new PC("StandaloneOverlayStorage","$ts-native"),
		new PC("StandalonePETCurveStorage","$ts-native"),
		new PC("StandaloneVOILUTStorage","$ts-native"),
		new PC("StereometricRelationshipStorage","$ts-native"),
		new PC("StructuredComprehensiveStorageRetired","$ts-native"),
		new PC("StructuredReportAudioStorageRetired","$ts-native"),
		new PC("StructuredReportDetailStorageRetired","$ts-native"),
		new PC("StructuredReportTextStorageRetired","$ts-native"),
		new PC("SurfaceSegmentationStorage","$ts-native"),
		//new PC("ToshibaUSPrivateDataStorage","$ts-native"),
		new PC("TwelveLeadECGWaveformStorage","$ts-native"),
		new PC("UltrasoundImageStorage","$ts-epd,$ts-native"),
		new PC("UltrasoundImageStorageRetired","$ts-native"),
		new PC("UltrasoundMultiframeImageStorage","$ts-epd,$ts-native"),
		new PC("UltrasoundMultiframeImageStorageRetired","$ts-native"),
		new PC("Verification","$ts-native"),
		new PC("VideoEndoscopicImageStorage","MPEG2"),
		new PC("VideoMicroscopicImageStorage","MPEG2"),
		new PC("VideoPhotographicImageStorage","MPEG2"),
		new PC("VLEndoscopicImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("VLImageStorageRetired","$ts-native"),
		new PC("VLMicroscopicImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("VLMultiframeImageStorageRetired","$ts-native"),
		new PC("VLPhotographicImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("VLSlideCoordinatesMicroscopicImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("VLWholeSlideMicroscopyImageStorage","$ts-jpeglossless,JPEGBaseline,$ts-native"),
		new PC("VOILUTBox","$ts-native"),
		new PC("XAXRFGrayscaleSoftcopyPresentationStateStorage","$ts-native"),
		new PC("XRay3DAngiographicImageStorage","$ts-jpeglossless,JPEGBaseline,$ts-native"),
		new PC("XRay3DCraniofacialImageStorage","$ts-jpeglossless,JPEGBaseline,$ts-native"),
		new PC("XRayAngiographicBiPlaneImageStorageRetired","$ts-native"),
		new PC("XRayAngiographicImageStorage","$ts-jpeglossless,JPEGBaseline,$ts-native"),
		new PC("XRayRadiationDoseSR","$ts-native"),
		new PC("XRayRadiofluoroscopicImageStorage","$ts-jpeglossless,$ts-native"),
		new PC("VLWholeSlideMicroscopyImageStorage","$ts-epd,$ts-native")
	};

	//SOP Classes not in the dcm4che UID dictionary
	static PC[] ext_pcs = { };
	
	static class SkipTable extends HashSet<String> {
		public SkipTable() {
			super();
			add(UIDs.forName("JPEG2000Lossless"));
			add(UIDs.forName("JPEG2000Lossy"));
		}
	}

}