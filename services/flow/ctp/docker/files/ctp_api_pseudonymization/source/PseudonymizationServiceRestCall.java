package org.rsna.ctp.dkfz;

import java.io.*;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

import org.apache.log4j.Logger;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.net.HttpURLConnection;


/**
 * @author hanno
 *
 */
public class PseudonymizationServiceRestCall {

	static final Logger logger = Logger.getLogger(PseudonymizationServiceRestCall.class);
	/**
	 * Identifier of this session.
	 */
	private static String name = "PseudonymizationServiceRestCall" ;
	private String sessionId= "";
	private String instanceURL;
	private String addPatientTokenId = "";
	private String queryInstanceApiKey;

	PseudonymizationServiceRestCall(String url, String apiKey){
		instanceURL = url;
		queryInstanceApiKey = apiKey;
	}


	/** Creates/opens session to of Mainzellist
	 * @throws Exception
	 */
	public void openSession() throws Exception {
		if(isSessionValid())
			return;
		logger.warn(name + ": openSession");
		System.out.println(name + ": openSession");
		URL url = new URL(instanceURL + "/sessions");
		logger.warn("URL sessions " + url);
		System.out.println("URL sessions " + url);
		HttpURLConnection conn = (HttpURLConnection) url.openConnection();
		conn.setRequestMethod("POST");
		conn = setConnectionDefaultTypes(conn);
		if (conn.getResponseCode() != HttpURLConnection.HTTP_CREATED) {
			logger.warn(name +": openSession returns: "+ conn.getResponseCode());
			System.out.println(name +": openSession returns: "+ conn.getResponseCode()+ "\n");
			exceptionMessage(conn);
		}
		try {
			BufferedReader br = new BufferedReader(new InputStreamReader(
					(conn.getInputStream())));
			JSONObject json = readBuffer(br);
			sessionId = json.getString("sessionId");
			br.close();
			conn.disconnect();
			logger.warn(name + ": sessionID " + sessionId);
			System.out.println(name + ": sessionID " + sessionId+ "\n");
		} catch (Exception e) {
			logger.error(name +": sessionID could not be correctly handled: " + conn.getResponseCode()) ;
			System.out.println(name +": sessionID could not be correctly handled: " + conn.getResponseCode());
			exceptionMessage(conn);
		}
	}


	/** adds a patient
	 * @param brithdayDay
	 * @param brithdayMonth
	 * @param birthdayYear
	 * @param firstName
	 * @param lastName
	 * @return the Pseudonym for the Patient
	 * @throws Exception
	 */
	public String addPatient(String brithdayDay, String brithdayMonth,String birthdayYear, String firstName, String lastName) throws Exception {
		logger.warn(name + " addPatient");
		System.out.println(name + " addPatient");
		addPatientTokenId = "";
		getAddPatientToken( brithdayDay, brithdayMonth,birthdayYear, firstName, lastName);
		URL url = new URL(instanceURL+ "/patients?mainzellisteApiVersion=3.0&tokenId=" + addPatientTokenId);
		HttpURLConnection conn = (HttpURLConnection) url.openConnection();
		conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");
		conn.setRequestProperty("Accept", "application/json");
		conn.setDoInput(true);
		conn.setRequestMethod("POST");

		//make sure mainzellist gets an pseudonym
		//sureness cannot be decoded within the data fields (during getAddPatientToken
		//it has to be set  during the pseudonym request in x-www-form-urlencoded
		String urlParameters  = "sureness=true";
		byte[] postData = urlParameters.getBytes( StandardCharsets.UTF_8 );
		int postDataLength = postData.length;
		conn.setRequestProperty("charset", "utf-8");
		conn.setRequestProperty("Content-Length", Integer.toString(postDataLength ));
		conn.setDoOutput(true);
		DataOutputStream st = new DataOutputStream(conn.getOutputStream());
		st.write(postData);
		st.flush();
		st.close();

		JSONObject json = readResponse(conn);
		String pseudonym = json.getString("idString");
		logger.warn("pseudonym: " + pseudonym);
		System.out.println("pseudonym: " + pseudonym + "\n");
		return 	pseudonym;

	}

	private void exceptionMessage(HttpURLConnection conn) throws Exception {
		InputStream errorBody;
		if (conn.getResponseCode() < HttpURLConnection.HTTP_BAD_REQUEST) {
			errorBody = conn.getInputStream();
		} else {
			/* error from server */
			errorBody = conn.getErrorStream();
		}
		BufferedReader in = new BufferedReader(
				new InputStreamReader(
						errorBody));

		StringBuilder response = new StringBuilder();
		String currentLine;

		while ((currentLine = in.readLine()) != null)
			response.append(currentLine);

		in.close();

		String read= response.toString();
		logger.warn(name +": connection returns: "+ read) ;
		System.out.println(name +": connection returns: "+ read + "\n") ;
		throw new IOException("Failed : HTTP error code : "
				+ conn.getResponseCode() + " --" + read);
	}

	private HttpURLConnection setConnectionDefaultTypes(HttpURLConnection conn)
	{
		conn.setRequestProperty("Accept", "application/json");
		conn.setRequestProperty("Content-Type", "application/json");
		conn.setRequestProperty("mainzellisteApiKey", queryInstanceApiKey);
		conn.setRequestProperty("mainzellisteApiVersion", "3.0");
		return conn;
	}

	/**
	 * @return true if valid, otherwice false (a new seesion has to be created
	 * @throws Exception
	 */
	private boolean isSessionValid() throws Exception {
		if("" == sessionId) {
			return false;
		}
		URL url = new URL(instanceURL + "/sessions/"+ sessionId);
		HttpURLConnection conn = (HttpURLConnection) url.openConnection();
		conn.setRequestMethod("GET");
		conn = setConnectionDefaultTypes(conn);
		if (conn.getResponseCode() != HttpURLConnection.HTTP_CREATED &&
				conn.getResponseCode() != HttpURLConnection.HTTP_OK) {
			conn.disconnect();
			return false;
		}
		conn.disconnect();
		return true;
	}

	/**
	 * adds the parameter to a JSONObject and creates a addPatient token in the Mainzelliste
	 * @param brithdayDay
	 * @param brithdayMonth
	 * @param birthdayYear
	 * @param firstName
	 * @param lastName
	 * @throws Exception
	 */
	private void getAddPatientToken(String brithdayDay, String brithdayMonth,String birthdayYear, String firstName, String lastName) throws Exception {
		URL url = new URL(instanceURL + "/sessions/"+ sessionId + "/tokens");
		HttpURLConnection conn = (HttpURLConnection) url.openConnection();
		conn.setRequestMethod("POST");
		conn.setRequestProperty("Accept", "application/json");
		conn.setRequestProperty("Content-Type", "application/json");
		conn.setRequestProperty("mainzellisteApiKey",queryInstanceApiKey);
		conn.setRequestProperty("mainzellisteApiVersion", "3.0");
		//conn = setConnectionDefaultTypes(conn);
		JSONObject data = new JSONObject();
		JSONObject post_data = new JSONObject();
		JSONObject fields = new JSONObject();
		fields.put("vorname", firstName);
		fields.put("nachname", lastName);
		fields.put("geburtsjahr", birthdayYear);
		fields.put("geburtsmonat", brithdayMonth);
		fields.put("geburtstag", brithdayDay);

		logger.warn(name + ": Fields; firstName " + firstName + " lastName "
				+ lastName + " birthyear " + birthdayYear) ;
		System.out.println(name + ": Fields; firstName " + firstName + " lastName "
				+ lastName + " birthyear " + birthdayYear + "\n") ;
		//fields.put("geburtsname", "");
		//fields.put("ort", "");
		//fields.put("plz", "");
		data.put("fields", fields);
		post_data.put("type", "addPatient");
		post_data.put("data", data);
		conn.setDoOutput(true);
		conn.setDoInput(true);
		conn.connect();

		OutputStreamWriter wr = new OutputStreamWriter(conn.getOutputStream());
		wr.write(post_data.toString());
		wr.flush();
		wr.close();

		JSONObject json = readResponse(conn);

		addPatientTokenId = json.getString("id");

		conn.disconnect();
	}

	/**
	 * @param conn the connection
	 * @return the buffer from the response
	 * @throws Exception
	 */
	private JSONObject readResponse(HttpURLConnection conn) throws Exception {

		if (conn.getResponseCode() != HttpURLConnection.HTTP_CREATED &&
				conn.getResponseCode() != HttpURLConnection.HTTP_OK) {
			exceptionMessage(conn);
		}

		BufferedReader br = new BufferedReader(new InputStreamReader(
				(conn.getInputStream())));;

		return readBuffer(br);
	}

	/**
	 * @param bufferedReader
	 * @return the JSONObject read
	 * @throws Exception, when no JSONObject coud be read
	 */
	private JSONObject readBuffer(BufferedReader bufferedReader) throws Exception {
		StringBuilder builder = new StringBuilder();
		String line;
		while ((line = bufferedReader.readLine()) != null) {
			builder.append(line);
		}
		bufferedReader.close();
		String lines = builder.toString();
		try {
			return new JSONObject(lines);
		}
		catch (JSONException ex) {
			try {
				JSONArray jsonArray =  new JSONArray(lines);
				JSONObject object = jsonArray.getJSONObject(0);
				return object;
			}
			catch (JSONException ex1) {
				return new JSONObject();
			}
		}
	}
}