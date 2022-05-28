/*---------------------------------------------------------------
*  Copyright 2015 by the Radiological Society of North America
*
*  This source software is released under the terms of the
*  RSNA Public License (http://mirc.rsna.org/rsnapubliclicense.pdf)
*----------------------------------------------------------------*/

package org.rsna.runner;

import java.awt.*;
import java.awt.event.*;
import java.io.*;
import java.net.*;
import java.util.*;
import javax.net.ssl.*;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.w3c.dom.NamedNodeMap;

/**
 * The ClinicalTrialProcessor program non-GUI runner.
 * This program starts and stops the CTP program.
 */
public class Runner {

	static File configFile = new File("config.xml");
	static File propsFile = new File("Launcher.properties");
	static File ctp = new File("libraries/CTP.jar");
	static int port = 0;
	static boolean ssl;
	static Properties props;

	public static void main(String args[]) {
		Document configXML = getDocument(configFile);
		port = getInt( getAttribute(configXML, "Server", "port"), 80 );
		ssl = getAttribute(configXML, "Server", "ssl").equals("yes");

		props = new Properties();
		try { if (propsFile.exists())  props.load( new FileInputStream( propsFile ) ); }
		catch (Exception useDefaults) { }

		String cmd = "toggle";
		if (args.length > 0) {
			String arg = args[0].trim().toLowerCase();
			if (arg.equals("help")) {
				help();
				System.exit(0);
			}
			else if (arg.equals("status")) {
				System.out.println("CTP is "+(isRunning()?"":"not ")+"running");
				System.exit(0);
			}
			if (!arg.equals("stop") && !arg.equals("start") && !arg.equals("toggle")) {
				help();
				System.out.println("Unknown command \""+arg+"\"");
				System.exit(0);
			}
			cmd = arg;
		}

		if (isRunning()) {
			if (cmd.equals("stop") || cmd.equals("toggle")) {
				System.out.println("Stopping CTP");
				shutdown();
			}
			else System.out.println("CTP is already running");
			System.exit(0);
		}

		else {
			if (cmd.equals ("start") || cmd.equals("toggle")) {
				//clearLogs();
				System.out.println("Starting CTP");
				Thread runner = startup();
				while (runner.isAlive()) {
					try { Thread.sleep(1000); }
					catch (Exception ex) { }
				}
				System.out.println("Runner: exit.");
			}
			else System.out.println("CTP is already stopped");
			System.exit(0);
		}
	}

	private static void help() {
		System.out.println("Usage: java -jar Runner.jar [command]");
		System.out.println("   [command]: start | stop | toggle | status | help");
		System.out.println("   default command: toggle");
	}

	private static Thread startup() {
		CTPRunner runner = new CTPRunner();
		runner.start();
		return runner;
	}

	static class CTPRunner extends Thread {
		public CTPRunner() {
			super("Runner");
		}
		public void run() {
			Runtime rt = Runtime.getRuntime();
			try {
				boolean osIsWindows = System.getProperty("os.name").toLowerCase().contains("windows");
				String ver = System.getProperty("java.version");
				String ext = System.getProperty("java.ext.dirs", "");
				String sep = System.getProperty("path.separator");
				String user = System.getProperty("user.dir");
				File dir = new File(user);

				ArrayList<String> command = new ArrayList<String>();

				command.add("java");

				//Set the maximum memory pool
				String maxHeap = props.getProperty("mx", "512");
				int mx = getInt(maxHeap, 512);
				mx = Math.max(mx, 128);
				command.add("-Xmx"+mx+"m");

				//Set the starting memory pool
				String minHeap = props.getProperty("ms", "128");
				int ms = getInt(minHeap, 128);
				ms = Math.max(ms, 128);
				command.add("-Xms"+ms+"m");

				//Set the Thread stack size, if defined in the props
				String stackSize = props.getProperty("ss", "");
				if (!stackSize.equals("")) {
					int ss = getInt(stackSize, 0);
					if (ss > 32) command.add("-Xss"+ss+"k");
				}

				String additionalProperties = props.getProperty("add", "");
				if (!additionalProperties.equals("")) {
					String[] parts = additionalProperties.split(" ");
					for (String part : parts) {
						command.add(part);
					}
				}

				//Set the extensions directories if Java 8 or less
				int n = ver.indexOf(".");
				if (n > 0) ver = ver.substring(0,n);
				n = Integer.parseInt(ver);
				if (n < 9) {
					String extDirs = props.getProperty("ext", "").trim();
					if (!extDirs.equals("") && !ext.equals("")) extDirs += sep;
					extDirs += ext;
					if (!extDirs.equals("")) {
						ext = "-Djava.ext.dirs=" + extDirs;
						if (ext.contains(" ") || ext.contains("\t")) ext = "\"" + ext + "\"";
						command.add(ext);
					}
				}

				//Set the program name
				command.add("-jar");
				command.add("libraries" + File.separator + "CTP.jar");

				String[] cmdarray = command.toArray( new String[command.size()] );

				for (String s : cmdarray) System.out.print(s + " ");
				System.out.println("");

				Process proc = rt.exec(cmdarray, null, dir);
				(new Streamer(proc.getErrorStream(), "stderr")).start();
				(new Streamer(proc.getInputStream(), "stdout")).start();

				int exitVal = proc.waitFor();
				System.out.println("Exit: " + ((exitVal==0) ? "normal" : "code "+exitVal));
			}
			catch (Exception ex) { ex.printStackTrace(); }
		}
	}

	static class Streamer extends Thread {
		InputStream is;
		String name;

		public Streamer(InputStream is, String name) {
			this.is = is;
			this.name = name;
		}

		public void run() {
			try {
				InputStreamReader isr = new InputStreamReader(is);
				BufferedReader br = new BufferedReader(isr);
				String line = null;
				while ( (line = br.readLine()) != null) {
					System.out.println(name + ": " + line);
				}
				System.out.println(name + ": " + "exit");
			}
			catch (Exception ignore) { }
		}
	}

    public static void shutdown() {
		try {
			String protocol = "http" + (ssl?"s":"");
			URL url = new URL( protocol, "127.0.0.1", port, "shutdown");

			HttpURLConnection conn = getConnection( url );
			conn.setRequestMethod("GET");
			conn.setRequestProperty("servicemanager", "shutdown");
			conn.connect();

			StringBuffer sb = new StringBuffer();
			BufferedReader br = new BufferedReader( new InputStreamReader(conn.getInputStream(), "UTF-8") );
			int n; char[] cbuf = new char[1024];
			while ((n=br.read(cbuf, 0, cbuf.length)) != -1) sb.append(cbuf,0,n);
			br.close();
			System.out.println( sb.toString().replace("<br>","\n") );
		}
		catch (Exception ex) { }
	}

	public static boolean isRunning() {
		try {
			URL url = new URL("http" + (ssl?"s":"") + "://127.0.0.1:"+port);
			HttpURLConnection conn = getConnection( url );
			conn.setRequestMethod("GET");
			conn.connect();
			int length = conn.getContentLength();
			StringBuffer text = new StringBuffer();
			InputStream is = conn.getInputStream();
			InputStreamReader isr = new InputStreamReader(is);
			int size = 256; char[] buf = new char[size]; int len;
			while ((len=isr.read(buf,0,size)) != -1) text.append(buf,0,len);
			return true;
		}
		catch (Exception ex) { return false; }
	}

	public static void wait(int ms) {
		try { Thread.sleep(ms); }
		catch (Exception ex) { }
	}

	public static HttpURLConnection getConnection(URL url) throws Exception {
		String protocol = url.getProtocol().toLowerCase();
		if (!protocol.startsWith("https") && !protocol.startsWith("http")) {
			throw new Exception("Unsupported protocol ("+protocol+")");
		}
		HttpURLConnection conn;
		if (protocol.startsWith("https")) {
			HttpsURLConnection httpsConn = (HttpsURLConnection)url.openConnection();
			httpsConn.setHostnameVerifier(new AcceptAllHostnameVerifier());
			httpsConn.setUseCaches(false);
			httpsConn.setDefaultUseCaches(false);
			conn = httpsConn;
		}
		else conn = (HttpURLConnection)url.openConnection();
		conn.setDoOutput(true);
		conn.setDoInput(true);
		return conn;
	}

	static class AcceptAllHostnameVerifier implements HostnameVerifier {
		public boolean verify(String urlHost, SSLSession ssls) {
			return true;
		}
	}

	public static void clearLogs() {
		File logs = new File("logs");
		if (logs.exists()) {
			File[] files = logs.listFiles();
			for (File f : files) deleteAll(f);
		}
	}

	public static void deleteAll(File file) {
		if (file.isFile()) file.delete();
		else {
			File[] files = file.listFiles();
			for (File f : files) deleteAll(f);
		}
	}
	
	public static int getInt(String theString, int defaultValue) {
		if (theString == null) return defaultValue;
		theString = theString.trim();
		if (theString.equals("")) return defaultValue;
		try { return Integer.parseInt(theString); }
		catch (NumberFormatException e) { return defaultValue; }
	}

	public static Document getDocument(File file) {
		try {
			DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
			dbf.setNamespaceAware(true);
			DocumentBuilder db = dbf.newDocumentBuilder();
			return db.parse(file);
		}
		catch (Exception ex) { return null; }
	}

	public static String getAttribute( Document doc, String eName, String aName ) {
		Element root = doc.getDocumentElement();
		NodeList nl = root.getElementsByTagName( eName );
		for (int i=0; i<nl.getLength(); i++) {
			String attr = ((Element)nl.item(i)).getAttribute( aName ).trim();
			if (!attr.equals("")) return attr;
		}
		return "";
	}

}

