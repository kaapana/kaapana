package org.rsna.ctp.dkfz;


import java.util.Properties;

import org.apache.log4j.Logger;
import org.rsna.ctp.objects.DicomObject;
import org.rsna.ctp.objects.FileObject;
import org.rsna.ctp.pipeline.Processor;
import org.rsna.ctp.stdstages.DicomAnonymizer;
import org.rsna.ctp.stdstages.anonymizer.dicom.DAScript;
import org.w3c.dom.Element;




/**
 * The Dicom Pseudonymizer calling an api
 *
 */
public class DicomApiPseudonymizer extends DicomAnonymizer implements Processor {

	static final Logger logger = Logger.getLogger(DicomApiPseudonymizer.class);

	private String queryInstance; //IP of calling service (set in atr default)
	private String patientName;
	private String lastItempatientName = "";
	private String firstName;
	private String lastName;
	private String birthday;
	private String brithdayDay;
	private String brithdayMonth;
	private String birthdayYear;
	private String lastPseudonym= "";
	private String lastBirthday = "";

	//if mainzelliste use this..
	private PseudonymizationServiceRestCall pseudonymizationServiceRestCall;


	/**
	 * @param element
	 */
	public DicomApiPseudonymizer(Element element) {
		super(element);
		queryInstance = element.getAttribute("queryInstance");
		String apiKey = element.getAttribute("queryInstanceApiKey");
		pseudonymizationServiceRestCall = new PseudonymizationServiceRestCall(queryInstance, apiKey);
	}

	/**
	 *
	 */
	@Override
	public FileObject process(FileObject fileObject) {
		return 	queryProcess(fileObject);
	}


	/**
	 * @param fileObject
	 * @return
	 */
	private FileObject queryProcess(FileObject fileObject) {
		String pseudonym = "";

		if (fileObject instanceof DicomObject) {
			DicomObject dicomObject = (DicomObject)fileObject;
			// Patient's Name (0010,0010) lastname,firstname
			patientName = getElementValue(dicomObject, "00100010");
			if (patientName.contains(",")) {
				String[] parts = patientName.split(",");
				firstName = parts[1];
				lastName = parts[0];
			}
			else {
				if(patientName.isEmpty())
				{

					logger.warn(name + " Dicom Tag PatientName is empty, " +
							"therefore leaving pseudonym as empty string!");
					System.out.println(name + "Dicom Tag PatientName is empty, " +
							"therefore leaving pseudonym as empty string!" + "\n");
					addPseudonymToScript("");
					return super.process(fileObject);
				}

				lastName = patientName;
				firstName = lastName;
			}
			//	Patient's Birth Date (0010,0030)
			birthday = getElementValue(dicomObject, "00100030");
			if( 8 == birthday.length()) {
				birthdayYear = birthday.substring(0,4);
				brithdayMonth = birthday.substring(4,6);
				brithdayDay = birthday.substring(6);
			}
			else {
				if(birthday.isEmpty())
				{
					logger.warn(name + " birthday field is empty, setting a default value");
					System.out.println(name + " birthday field is empty, setting a default value"+"\n");
				}
				logger.warn(name + " birthday has a wrong format " + birthday);
				System.out.println(name + " birthday has a wrong format " + birthday+ "\n");
				//setting dummy values
				birthdayYear = "2000";
				brithdayMonth = "01";
				brithdayDay = "01";
				birthday = "20000101";
			}
			if(patientName.equals(lastItempatientName) && birthday.equals(lastBirthday)
					&& !lastPseudonym.isEmpty())
			{
				addPseudonymToScript(lastPseudonym);
				return super.process(fileObject);
			}
			lastItempatientName = patientName;
			lastBirthday = birthday;
			try {
				pseudonym = queryPseudonym();
			} catch (Exception ex) {
				logger.error(name + ": Unable to query pseudonym " + ex);
				System.out.println(name+ ": Unable to query pseudonym " + ex + "\n");
				logger.error(name + ": The file is:" + fileObject);
				System.out.println(name + ": The file is:" + fileObject + "\n");
				//Quarantine the object
				//if (quarantine != null) quarantine.insert(fileObject);
				System.exit(1);
				return null;
			}
		}
		addPseudonymToScript(pseudonym);
		lastPseudonym = pseudonym;
		return super.process(fileObject);
	}

	private void addPseudonymToScript(String pseudonym) {
		DAScript dascript = DAScript.getInstance(scriptFile);
		Properties script = dascript.toProperties();
		script.setProperty("pseudonym", pseudonym);
	}

	/**
	 * @throws Exception
	 */
	private String queryPseudonym() throws Exception{
		pseudonymizationServiceRestCall.openSession();
		return pseudonymizationServiceRestCall.addPatient(brithdayDay, brithdayMonth, birthdayYear, firstName, lastName);

	}


	/**
	 * @param dicomObject
	 * @param tag
	 * @return tagValue
	 */
	private String getElementValue(DicomObject dicomObject, String tag) {
		String value = "";
		try {
			int[] tags = DicomObject.getTagArray(tag);
			value = dicomObject.getElementString(tags);
		} catch (Exception ex) {
			logger.warn(name + ": ......exception processing: " + tag);
			System.out.println(name + ": ......exception processing: " + tag + "\n");
		}
		return value;
	}

}