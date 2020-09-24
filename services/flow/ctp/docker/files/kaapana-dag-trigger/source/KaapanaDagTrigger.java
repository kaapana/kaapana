package org.rsna.ctp.dkfz;
import java.io.*;
import java.text.*;
import java.util.*;
import org.apache.log4j.Logger;
import org.rsna.ctp.objects.DicomObject;
import org.rsna.ctp.objects.FileObject;
import org.rsna.ctp.pipeline.*;
import org.rsna.ctp.stdstages.*;
import org.json.simple.JSONObject;
import java.net.HttpURLConnection;
import org.w3c.dom.Element;
import java.net.*;

/**
 * An Storage Service that stores files in directories and triggers airflow via http.
 */
public class KaapanaDagTrigger extends DirectoryStorageService {

	static final Logger logger = Logger.getLogger(KaapanaDagTrigger.class);

	String trigger_url;
	String name;
	String dag_id;
	String debug_log;
	int calledAETTag = 0;
	int callingAETTag = 0;
	int connectionIPTag = 0;
	int unchangedCounter = 2;
	String callingAET;
	String calledAET;
	String connectionIP;
	String studyDescription;
	String patientName;
	String patientID;
	String studyInstanceUID;
	String seriesInstanceUID;
	String current_uid = "";
	String username;
	String password;
	String fix_aetitle;
	boolean isTagSet = false;
	String removeTags = "no";
	final Object syncObject;

	/**
	 * Class constructor; creates a new instance of the ExportService.
	 *
	 * @param element the configuration element.
	 */
	public KaapanaDagTrigger(Element element) throws Exception {
		super(element);
		trigger_url = element.getAttribute("triggerurl");
		dag_id = element.getAttribute("dagnames");
		debug_log = element.getAttribute("debug_log");
		name = element.getAttribute("name");
		username = element.getAttribute("airflow_username");
		password = element.getAttribute("airflow_password");
		//routing aetitle Option, aetitle is always this string
		fix_aetitle = element.getAttribute("fix_aetitle");
		removeTags = element.getAttribute("remove_tags");
		String unChangedString = element.getAttribute("unchangedCounter");
		if(!unChangedString.isEmpty())
			unchangedCounter =Integer.parseInt(unChangedString.trim());
		syncObject = new Object();
	}


	/**
	 *
	 */
	void setImportServiceTags(){

		Pipeline pipeline = this.getPipeline();
		List<ImportService> importServiceList = pipeline.getImportServices();
		for (ImportService importService: importServiceList) {
			if(importService instanceof DicomImportService){
				DicomImportService dicomImportService = (DicomImportService)importService;
				//Get the calledAETTag, if any
				calledAETTag = dicomImportService.getCalledAETTag();
				//Get the callingAETTag, if any
				callingAETTag = dicomImportService.getCallingAETTag();
				//Get the connectionIPTag, if any
				connectionIPTag = dicomImportService.getConnectionIPTag();
				isTagSet = true;
			}
		}
	}

	/**
	 *
	 * @param fileObject the object to process.
	 * @return null for stored
	 */
	@Override
	public synchronized FileObject store(FileObject fileObject) {
		try {
			if (fileObject instanceof DicomObject) {
				if (!isTagSet && removeTags.equals("yes"))
					setImportServiceTags();
				DicomObject dicomObject = (DicomObject) fileObject;
				callingAET = "";
				calledAET = "";
				connectionIP = "";
				if(removeTags.equals("yes"))
				{
					if ((calledAETTag != 0)
							|| (callingAETTag != 0)
							|| (connectionIPTag != 0))
						fileObject = resetTags(fileObject);
				}
				if(!fix_aetitle.equals(""))
					calledAET = fix_aetitle;
				//store after changing tags, but before triggering airflow
				int fileCount;
				File storedFileParentDir;
				synchronized (syncObject)
				{
					FileObject storedFileObject = super.store(fileObject);
					File storedFile = storedFileObject.getFile();
					storedFileParentDir = storedFile.getParentFile();
					//get number of Files in Folder, if this is the first file trigger/retrigger airflow
					fileCount = Objects.requireNonNull(storedFileParentDir.list()).length;
				}

				seriesInstanceUID = getElementValue(dicomObject, "0020000E");
				current_uid = seriesInstanceUID;

				if( 1 == fileCount){
					studyDescription = getElementValue(dicomObject, "00081030");
					patientName = getElementValue(dicomObject, "00100010");
					patientID = getElementValue(dicomObject, "00100020");
					studyInstanceUID = getElementValue(dicomObject, "0020000D");
					logger.warn("Send to Airflow seriesInstanceUID " + seriesInstanceUID);
					send(storedFileParentDir);
				}
				else {
					if (debug_log.equals("yes")) {
						logger.warn("UID already triggered: " + current_uid);
						logger.warn("Number of files in folder " + fileCount);
					}
				}
			} else {
				logger.warn(name + ": " + fileObject + " is not instance of DicomObject");
				if (quarantine != null)
					quarantine.insert(fileObject);
				return null;
			}

			return fileObject;
		} catch (Exception e) {
			logger.warn(name + ": Unable to trigger Airflow for: " + fileObject);
			e.printStackTrace();
			logger.warn(e);
			if (quarantine != null) quarantine.insert(fileObject);
			return null;
		}
	}

	/**
	 *
	 * @param storedFileParentDir the parent dir of the stored file
	 * @throws Exception
	 */
	private void send(File storedFileParentDir) throws Exception {
		logger.warn(name + ": Triggering: " + dag_id + " - " + current_uid);
		JSONObject post_data = new JSONObject();
		JSONObject conf = new JSONObject();

		conf.put("callingAET", callingAET);
		conf.put("calledAET", calledAET);
		conf.put("connectionIP", connectionIP);
		conf.put("patientID", patientID);
		conf.put("studyInstanceUID", studyInstanceUID);
		conf.put("seriesInstanceUID", seriesInstanceUID);

		String timestampString = new SimpleDateFormat("_yyyyMMddHHmmss").format(new Date());
		String dicomPath = current_uid + timestampString;
		logger.warn("Dicom Path: " + dicomPath);
		conf.put("dicom_path", dicomPath);

		post_data.put("conf", conf);
		Thread thread = new DelayedAirflowTrigger(storedFileParentDir, syncObject, post_data, dicomPath);
		thread.start();
	}

	/**
	 *
	 * @param dob the dicom object
	 * @param group the tag
	 * @return
	 */
	private String getElementValue(DicomObject dob, String group) {
		String value = "";
		try {
			int[] tags = DicomObject.getTagArray(group);
			value = dob.getElementString(tags);
		} catch (Exception ex) {
			logger.warn(name + ": ......exception processing: " + group);
			logger.warn(ex);
		}
		return value;
	}

	/**
	 * reset Tags for Triggered Files only
	 * When storing file via another export (e.g. dicom) before triggering
	 * this exported files still have not reseted values.
	 * @param fo file object
	 * @return
	 */
	private FileObject resetTags(FileObject fo) {
		try {
			DicomObject dob = new DicomObject(fo.getFile(), true); //leave the stream open
			File dobFile = dob.getFile();
			if (0 != callingAETTag) {
				callingAET = dob.getElementValue(callingAETTag);
				//delete value of DICOM-Tag before sending
				dob.setElementValue(callingAETTag, "");
				String calling = dob.getElementValue(callingAETTag);
				logger.warn(calling);
			}
			if (0 != calledAETTag) {
				calledAET = dob.getElementValue(calledAETTag);
				dob.setElementValue(calledAETTag, "");
			}
			if (0 != connectionIPTag) {
				connectionIP = dob.getElementValue(connectionIPTag);
				dob.setElementValue(connectionIPTag, "");
			}

			File tFile = File.createTempFile("TMP-",".dcm",dobFile.getParentFile());
			dob.saveAs(tFile, false);
			dob.close();
			dob.getFile().delete();

			//Okay, we have saved the modified file in the temp file
			//and deleted the original file; now rename the temp file
			//to the original name so nobody is the wiser.
			tFile.renameTo(dobFile);

			//And finally parse it again so we have a real object to process.
			return new DicomObject(dobFile);
		}
		catch (Exception ex) {
			logger.warn("Unable to set read and reset Tags: \"");
			logger.warn("                               in: "+fo.getFile());
		}
		return fo;
	}

	/**
	 *
	 */
	class DelayedAirflowTrigger extends Thread {
		final Object syncObject;
		File storedFileParentDir;
		JSONObject postData;
		String dicomPath;

		/**
		 * @param storedParentDir
		 * @param obj
		 * @param postDataObj
		 * @param dicomPathName
		 */
		DelayedAirflowTrigger(File storedParentDir, Object obj, JSONObject postDataObj, String dicomPathName) {
			syncObject = obj;
			storedFileParentDir = storedParentDir;
			postData = postDataObj;
			dicomPath = dicomPathName;
		}

		/**
		 *
		 */
		public void run() {
			try {
				int dicomFileCount = Objects.requireNonNull(storedFileParentDir.list()).length;
				int noChangeCount = 0;
				//with 2 secs sleep the
				// min time without changes is 2*unchangedCounter secs
				// the max less then 2+2*unchangedCounter secs
				while (noChangeCount < unchangedCounter) {
					Thread.sleep(2000);
					int newDicomFileCount = Objects.requireNonNull(storedFileParentDir.list()).length;
					if (newDicomFileCount == dicomFileCount) {
						noChangeCount++;
					} else
						noChangeCount = 0;
					dicomFileCount = newDicomFileCount;
				}

				//lock writing to folder while renaming
				synchronized (syncObject) {
					logger.warn("Final file-count: " + dicomFileCount);
					logger.warn("Dicom Folder send to airflow: " + dicomPath);
					renameFolder();
				}
				triggerAirflow(postData, dag_id);
			} catch (Exception e) {
				logger.warn(name + ": Unable to trigger Airflow for: " + dicomPath);
				logger.warn(e);
				folderFilesToQuarantine(storedFileParentDir);
			}
		}

		/**
		 *
		 */
		private void folderFilesToQuarantine(final File folder) {
			try {
				if (quarantine != null) {
					for (final File fileEntry : Objects.requireNonNull(folder.listFiles())) {
						if (fileEntry.isDirectory()) {
							folderFilesToQuarantine(fileEntry);
						} else {
							FileObject fileObject = new FileObject(fileEntry);
							quarantine.insert(fileObject);
							logger.warn(fileEntry.getName() + "added to quarantine");
						}
					}
				}
			}
			catch (Exception e){
				logger.warn("files not added to quarantine: " + folder);
			}
		}

		/**
		 *
		 */
		private void renameFolder() {
			if (storedFileParentDir.isDirectory()) {
				File dirNew = new File(storedFileParentDir.getParent() + File.separator + dicomPath);
				storedFileParentDir.renameTo(dirNew);
				storedFileParentDir = dirNew;
			}
		}

		/**
		 * @param content
		 * @param dag_id
		 * @return
		 * @throws Exception
		 */
		private boolean triggerAirflow(JSONObject content, String dag_id) throws Exception {
			String url = trigger_url + "/" + dag_id;
			logger.warn(name + ": URL: " + url);
			URL object = new URL(url);
			HttpURLConnection con = (HttpURLConnection) object.openConnection();

			if (username != null && !username.isEmpty() && password != null && !password.isEmpty()) {
				String userpass = username + ":" + password;
				String basicAuth = "Basic " + new String(Base64.getEncoder().encode(userpass.getBytes()));
				con.setRequestProperty("Authorization", basicAuth);
			}

			con.setDoOutput(true);
			con.setDoInput(true);
			con.setRequestProperty("Content-Type", "application/json");
			con.setRequestProperty("Accept", "application/json");
			con.setRequestMethod("POST");

			OutputStreamWriter wr = new OutputStreamWriter(con.getOutputStream());
			wr.write(content.toString());
			wr.flush();

			// display what returns the POST request

			StringBuilder sb = new StringBuilder();
			int HttpResult = con.getResponseCode();
			if (HttpResult == HttpURLConnection.HTTP_OK) {
				BufferedReader br = new BufferedReader(new InputStreamReader(con.getInputStream(), "utf-8"));
				String line = null;
				while ((line = br.readLine()) != null) {
					sb.append(line + "\n");
				}
				br.close();
				logger.warn(name + ": " + sb.toString());
			} else {
				logger.warn(name + " HttpResult: " + HttpResult);
				logger.warn("Airflow was not triggered!");
				logger.warn("Dicom Folder not send to airflow: " + dicomPath);
				logger.warn("Resonse message: ");
				logger.warn(con.getResponseMessage());
				folderFilesToQuarantine(storedFileParentDir);
			}
			return true;
		}
	}
}

