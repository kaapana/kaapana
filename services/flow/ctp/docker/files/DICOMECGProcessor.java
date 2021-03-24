/*---------------------------------------------------------------
*  Copyright 2020 by the Radiological Society of North America
*
*  This source software is released under the terms of the
*  RSNA Public License (http://mirc.rsna.org/rsnapubliclicense.pdf)
*----------------------------------------------------------------*/

package org.rsna.ctp.stdstages.anonymizer.dicom;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.ByteArrayOutputStream;
import java.io.EOFException;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.math.BigInteger;
import java.nio.ByteOrder;
import java.security.*;
import java.text.SimpleDateFormat;
import java.util.Arrays;
import java.util.Calendar;
import java.util.Enumeration;
import java.util.GregorianCalendar;
import java.util.HashSet;
import java.util.Hashtable;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.Locale;
import java.util.Properties;
import java.nio.ByteBuffer;
import java.nio.ShortBuffer;
import java.awt.*;
import java.awt.image.*;

import org.dcm4che.data.Dataset;
import org.dcm4che.data.DcmDecodeParam;
import org.dcm4che.data.DcmElement;
import org.dcm4che.data.DcmEncodeParam;
import org.dcm4che.data.DcmObject;
import org.dcm4che.data.DcmObjectFactory;
import org.dcm4che.data.DcmParser;
import org.dcm4che.data.DcmParserFactory;
import org.dcm4che.data.FileFormat;
import org.dcm4che.data.FileMetaInfo;
import org.dcm4che.data.SpecificCharacterSet;
import org.dcm4che.dict.DictionaryFactory;
import org.dcm4che.dict.Status;
import org.dcm4che.dict.TagDictionary;
import org.dcm4che.dict.Tags;
import org.dcm4che.dict.UIDs;
import org.dcm4che.dict.VRs;

import org.rsna.ctp.stdstages.anonymizer.AnonymizerStatus;

import org.rsna.util.FileUtil;
import org.rsna.util.StringUtil;

import org.apache.log4j.Logger;

/**
 * The MIRC DICOM WaveForm Processor. The stage creates waveform
 * images for files that contain waveforms but no images.
 */
public class DICOMECGProcessor {

	static final Logger logger = Logger.getLogger(DICOMECGProcessor.class);
	static final DcmParserFactory pFact = DcmParserFactory.getInstance();
	static final DcmObjectFactory oFact = DcmObjectFactory.getInstance();
	static final DictionaryFactory dFact = DictionaryFactory.getInstance();
	static final TagDictionary tagDictionary = dFact.getDefaultTagDictionary();

   /**
     * Anonymizes the input file, writing the result to the output file.
     * The input and output files are allowed to be the same.
     * <p>
     * Important note: if the result is a AnonymizerStatus.SKIP or 
     * AnonymizerStatus.QUARANTINE, the output file is not written and the 
     * input file is unmodified, even if it is the same as the output file.
     * @param inFile the file to anonymize.
     * @param outFile the output file.  It may be same as inFile if you want
     * to anonymize in place.
     * @return the static status result
     */
    public static AnonymizerStatus process(File inFile, File outFile, boolean synthesizeMissingLeads, String format) {

		String exceptions = "";
		BufferedInputStream in = null;
		BufferedOutputStream out = null;
		File tempFile = null;
		byte[] buffer = new byte[4096];
		try {
			//Get the full dataset and leave the input stream open.
			in = new BufferedInputStream(new FileInputStream(inFile));
			DcmParser parser = pFact.newDcmParser(in);
			FileFormat fileFormat = parser.detectFileFormat();
			if (fileFormat == null) throw new IOException("Unrecognized file format: "+inFile);
			Dataset dataset = oFact.newDataset();
			parser.setDcmHandler(dataset.getDcmHandler());
			parser.parseDcmFile(fileFormat, -1);
			
			//Set a default for the SpecificCharacterSet, if necessary.
			SpecificCharacterSet cs = dataset.getSpecificCharacterSet();
			if (cs == null) dataset.putCS(Tags.SpecificCharacterSet, "ISO_IR 100");

			//Create the waveform image
			byte[] imageBytes = createWaveformImage(dataset, synthesizeMissingLeads, format);
			
			//Set the encoding
			DcmDecodeParam fileParam = parser.getDcmDecodeParam();
        	String prefEncodingUID = UIDs.ExplicitVRLittleEndian;
			FileMetaInfo fmi = dataset.getFileMetaInfo();
            if (fmi != null) prefEncodingUID = fmi.getTransferSyntaxUID();
			else prefEncodingUID = UIDs.ExplicitVRLittleEndian;
			DcmEncodeParam encoding = (DcmEncodeParam)DcmDecodeParam.valueOf(prefEncodingUID);

			//Write the dataset to a temporary file in the same directory
			File tempDir = outFile.getParentFile();
			tempFile = File.createTempFile("DCMtemp-", ".ecg", tempDir);
            out = new BufferedOutputStream(new FileOutputStream(tempFile));

            //Create and write the metainfo for the encoding we are using
			fmi = oFact.newFileMetaInfo(dataset, prefEncodingUID);
            dataset.setFileMetaInfo(fmi);
            fmi.write(out);

			//Write the dataset as far as was parsed
			dataset.writeDataset(out, encoding);
			
			//Write the PixelData element
			dataset.writeHeader(
				out,
				encoding,
				Tags.PixelData,
				VRs.OW,
				imageBytes.length);
			out.write(imageBytes);

			out.flush();
			out.close();
			in.close();

			//Rename the temp file to the specified outFile.
			if (outFile.exists() && !outFile.delete()) {
				logger.warn("Unable to delete " + outFile);
			}
			if (!tempFile.renameTo(outFile)) {
				logger.warn("Unable to rename "+ tempFile + " to " + outFile);
			}
		}

		catch (Exception e) {
			FileUtil.close(in);
			FileUtil.close(out);
			FileUtil.deleteAll(tempFile);
			//Now figure out what kind of response to return.
			String msg = e.getMessage();
			if (msg == null) {
				msg = "!error! - no message";
				logger.info("Error call from "+inFile, e);
				return AnonymizerStatus.QUARANTINE(inFile,msg);
			}
			if (msg.contains("!skip!")) {
				return AnonymizerStatus.SKIP(inFile,msg);
			}
			if (msg.contains("!quarantine!")) {
				logger.info("Quarantine call from "+inFile);
				logger.info("...Message: "+msg);
				return AnonymizerStatus.QUARANTINE(inFile,msg);
			}
			logger.info("Unknown exception from "+inFile, e);
			return AnonymizerStatus.QUARANTINE(inFile,msg);
		}
		return AnonymizerStatus.OK(outFile, exceptions);
    }
    
    private static byte[] createWaveformImage(Dataset ds, boolean synthesizeMissingLeads, String format) throws Exception {
		//Find a WaveformSeq item dataset with WaveformOriginality == ORIGINAL
 		DcmElement waveformSeq = ds.get(Tags.WaveformSeq);
		if (waveformSeq == null) {
			logger.warn("No WaveformSeq element");
			return null;
		}
		Dataset item = null;
		for (int i=0; (item = waveformSeq.getItem(i)) != null; i++ ) {
			String originality = item.getString(Tags.WaveformOriginality);
			if (originality.equals("ORIGINAL")) break; //pick the first one
		}
		if (item == null) {
			logger.warn("No  ORIGINAL waveform found");
			return null;
		}
		
		int nChannels = item.getInt(Tags.NumberOfWaveformChannels, 0);
		int nSamples = item.getInt(Tags.NumberOfWaveformSamples, 0);
		double samplingFrequency = item.getFloat(Tags.SamplingFrequency, 0);
		
		//Get the WaveformData
		DcmElement wd = item.get(Tags.WaveformData);
		int length = wd.length();
		int bytesPerSample = length/nChannels/nSamples;
		ByteBuffer bb = wd.getByteBuffer();
		ShortBuffer sb = bb.asShortBuffer();
		int[][] data = new int[nChannels][nSamples];
		int k=0;
		for (int x=0; x<nSamples; x++) {
			for (int c=0; c<nChannels; c++) {
				int y = sb.get(k++);
				data[c][x] = y;
			}
		}
		
		//Get the channel definitions and set the waveform data
		Channels cTable = new Channels();
		DcmElement defs = item.get(Tags.ChannelDefinitionSeq);
		for (int i=0; i<nChannels; i++) {
			Dataset ch = defs.getItem(i);
			if (ch == null) {
				logger.warn("Unable to get the channels");
				return null;
			}
			Channel c = new Channel(ch);
			c.setData(data[i]);
			cTable.put(c);
		}
		
		//Okay, figure out whether we have to synthesize missing leads
		if (synthesizeMissingLeads) {
			if (cTable.get("iii") == null) cTable.makeIII();
			if (cTable.get("avr") == null) cTable.makeAVR();
			if (cTable.get("avl") == null) cTable.makeAVL();
			if (cTable.get("avf") == null) cTable.makeAVF();
			//fix the channel count to account for the new channels
			nChannels = cTable.size();
		}
		
		//Determine the x and y scales
		int pixelsPerMM = 4;
		int headerHeight = 114; //pixels
		int leftMarginInPixels = 5 * pixelsPerMM; //1 box (5mm) indent for waveform graphs
		int verticalMMPerChannel = 20;
		int channelVerticalOriginInMM = 15;
		int channelVerticalOriginInPixels = channelVerticalOriginInMM * pixelsPerMM;
		int verticalPixelsPerChannel = verticalMMPerChannel * pixelsPerMM;
		int totalVerticalPixelsForChannels = (nChannels+1) * verticalPixelsPerChannel; //one extra channel bar at bottom
		double samplesPerMM = samplingFrequency/25;
		double samplePixelsPerUnit = 10 * pixelsPerMM * cTable.get("i").sensitivity / 1000.0;
		double channelTimeInSeconds = nSamples/samplingFrequency;
		double channelWidthInMM = nSamples/samplesPerMM;
		double channelWidthInPixels = channelWidthInMM * pixelsPerMM;
		double xScale = samplesPerMM / pixelsPerMM;
		double yScale = samplePixelsPerUnit;
		
		int width = (int)(leftMarginInPixels + channelWidthInPixels); //full width of graph paper
		int height = headerHeight + totalVerticalPixelsForChannels; //total height including header and extra space at bottom
		BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
		
		//Draw the graph paper
		Graphics2D g2d = (Graphics2D)image.getGraphics();
		g2d.setColor(Color.WHITE);
		g2d.fillRect(0, 0, width, height);
		g2d.setColor(Color.PINK);
		int boxSize = 5 * pixelsPerMM; //5mm boxes
		//Draw grid dots
		for (int x=0; x<width; x+=pixelsPerMM) {
			for (int y=headerHeight; y<height; y+=pixelsPerMM) {
				g2d.fillRect(x, y, 1, 1);
			}
		}
		//Draw grid lines
		for (int x=0; x<width; x+=boxSize) {
			g2d.drawLine(x, headerHeight, x, height-1);
		}
		for (int y=headerHeight; y<height; y+=boxSize) {
			g2d.drawLine(0, y, width-1, y);
		}
		
		//Draw the metadata
		Font font = new Font( "SansSerif", java.awt.Font.BOLD, 16 );
		g2d.setColor(Color.BLACK);
		drawMetadata(g2d, "", ds.getString(Tags.PatientName), 10, 18);
		drawMetadata(g2d, "ID: ", ds.getString(Tags.PatientID), 10, 36);
		drawMetadata(g2d, "DOB: ", fixDate(ds.getString(Tags.PatientBirthDate)), 10, 54);
		String sex = ds.getString(Tags.PatientSex);
		if (sex == null) sex = "";
		sex = sex.trim().toUpperCase();
		sex = (sex.startsWith("M") ? "Male" : sex.startsWith("F") ? "Female" : "");
		drawMetadata(g2d, "Sex: ", sex, 10, 72);
		drawMetadata(g2d, "Length: ", ds.getString(Tags.PatientSize), 10, 90);
		drawMetadata(g2d, "Weight: ", ds.getString(Tags.PatientWeight), 10, 108);
		
		Annotations annotations = new Annotations(ds);
		String[] keys = annotations.keySet().toArray(new String[annotations.size()]);
		Arrays.sort(keys);
		int colX = 10;
		int colY = 18;
		k = 0;
		while (k < keys.length) {
			colX += width/4;
			colY = 18;
			for (int i=0; i<6 && k<keys.length; i++, k++) {
				drawMetadata(g2d, keys[k]+": ", annotations.get(keys[k]), colX, colY);
				colY += 18;
			}
		}
		drawMetadata(g2d, "StudyDate: ", fixDate(ds.getString(Tags.StudyDate)), colX, colY);
				
		//Draw the starting pulses and scale
		for (int i=0; i<nChannels; i++) {
			int yOrigin = (verticalPixelsPerChannel * i) + channelVerticalOriginInPixels + headerHeight;
			g2d.drawLine(0, yOrigin, 0, yOrigin-10*pixelsPerMM);
			g2d.drawLine(0, yOrigin-10*pixelsPerMM, 5*pixelsPerMM, yOrigin-10*pixelsPerMM);
			g2d.drawLine(5*pixelsPerMM, yOrigin-10*pixelsPerMM, 5*pixelsPerMM, yOrigin);
		}
		int yLineBottom = height - 10*pixelsPerMM;
		int yLineTop = yLineBottom - 100*pixelsPerMM;
		int xLine = width - 2*pixelsPerMM;
		g2d.drawLine(xLine, yLineTop, xLine, yLineBottom);
		for (int i=0; i<11; i++) {
			int y = yLineTop + i*10*pixelsPerMM;
			g2d.drawLine( xLine - 6*pixelsPerMM, y, xLine, y);
			y += 5*pixelsPerMM;
			if (i < 10) {
				g2d.drawLine(xLine - 3*pixelsPerMM, y, xLine, y);
			}
		}
		FontMetrics fm = g2d.getFontMetrics(font);
		int adv = fm.stringWidth("10 cm");
		g2d.drawString("10 cm", xLine-adv, yLineBottom+5*pixelsPerMM);
		g2d.drawString("* synthesized", leftMarginInPixels, yLineBottom+5*pixelsPerMM);
		
		//Plot the waveforms and labels
		Channel[] channels = cTable.getChannels();
		for (int c=0; c<nChannels; c++) {
			int yOrigin = (verticalPixelsPerChannel * c) + channelVerticalOriginInPixels + headerHeight;
			channels[c].draw(g2d, (int)channelWidthInPixels, leftMarginInPixels, yOrigin, xScale, yScale, pixelsPerMM);
		}
		
		//Add the image to the dataset
		ds.putCS(Tags.PhotometricInterpretation, "RGB");
		ds.putUS(Tags.Rows, height);
		ds.putUS(Tags.Columns, width);
		ds.putUS(Tags.BitsAllocated, 8);
		ds.putUS(Tags.BitsStored, 8);
		ds.putUS(Tags.HighBit, 7);
		ds.putUS(Tags.SamplesPerPixel, 3);
		ds.putUS(Tags.PixelRepresentation, 0);
		ds.putUS(Tags.PlanarConfiguration, 0);
		
		//Return the array of pixels
		int[] pixels = new int[width * height * 3];
		pixels = image.getRaster().getPixels(0, 0, width, height, pixels);
		byte[] bytes = new byte[pixels.length];
		for (int i=0; i<bytes.length; i++) {
			bytes[i] = (byte)(pixels[i] & 0xff);
		}
		return bytes;
	}
	
	static void drawMetadata(Graphics g2d, String name, String value, int x, int y) {
		if (value == null) value = "";
		g2d.drawString(name + value, x, y);
	}
	
	static String fixDate(String date) {
		if (date == null) return "";
		if (date.length() > 8) date = date.substring(0, 8);
		if (date.length() == 8) {
			date = date.substring(0,4) 
					 + "." + date.substring(4,6) 
						+ "." + date.substring(6);
		}
		return date;
	}
	
	static class Annotations extends Hashtable<String,String> {
		public Annotations(Dataset ds) {
			super();
			DcmElement seq = ds.get(Tags.AnnotationSeq);
			if (seq != null) {
				Dataset item = null;
				for (int i=0; (item = seq.getItem(i)) != null; i++ ) {
					try {
						DcmElement mucs = item.get(Tags.MeasurementUnitsCodeSeq);
						String units = mucs.getItem(0).getString(Tags.CodeValue);
						DcmElement cncs = item.get(Tags.ConceptNameCodeSeq);
						String concept = cncs.getItem(0).getString(Tags.CodeMeaning);
						String v = item.getString(Tags.NumericValue);
						put(concept, String.format("%s %s", v, units));
					}
					catch (Exception skip) { }
				}
			}
		}
		public void log() {
			for (String k : keySet()) {
				logger.info(k + ": " + get(k));
			}
		}
	}
	
	static class Channels extends Hashtable<String,Channel> {
		public Channels() {
			super();
		}
		public void put(Channel c) {
			super.put(c.getLeadName(), c);
		}
		public boolean hasSyntheticChannel() {
			for (Channel c : values()) {
				if (c.isSynthetic()) return true;
			}
			return false;
		}
		public Channel[] getChannels() {
			LinkedList<Channel> cs = new LinkedList<Channel>();
			Channel c;
			if ( (c=get("i")) != null ) cs.add(c);
			if ( (c=get("ii")) != null ) cs.add(c);
			if ( (c=get("iii")) != null ) cs.add(c);
			if ( (c=get("avr")) != null ) cs.add(c);
			if ( (c=get("avl")) != null ) cs.add(c);
			if ( (c=get("avf")) != null ) cs.add(c);
			if ( (c=get("v1")) != null ) cs.add(c);
			if ( (c=get("v2")) != null ) cs.add(c);
			if ( (c=get("v3")) != null ) cs.add(c);
			if ( (c=get("v4")) != null ) cs.add(c);
			if ( (c=get("v5")) != null ) cs.add(c);
			if ( (c=get("v6")) != null ) cs.add(c);
			return cs.toArray(new Channel[cs.size()]);
		}
		public void makeIII() {
			//Lead
			try {
				int[] d1 = get("i").data;
				int[] d2 = get("ii").data;
				int[] d3 = new int[d1.length];
				for (int i=0; i<d3.length; i++) {
					d3[i] = d2[i] - d1[i];
				}
				Channel c = new Channel("III");
				c.setData(d3);
				c.setSynthetic();
				put(c);
			}
			catch (Exception unable) { }
		}
		public void makeAVR() {
			//-aVR = (I + II) / 2 
			try {
				int[] d1 = get("i").data;
				int[] d2 = get("ii").data;
				int[] dAVR = new int[d1.length];
				for (int i=0; i<dAVR.length; i++) {
					dAVR[i] = -(d2[i] + d1[i])/2;
				}
				Channel c = new Channel("aVR");
				c.setData(dAVR);
				c.setSynthetic();
				put(c);
			}
			catch (Exception unable) { }
		}
		public void makeAVL() {
			//aVL = (I - III) / 2 
			//    = (I - (II - I))/2
			//    = I - II/2
			try {
				int[] d1 = get("i").data;
				int[] d2 = get("ii").data;
				int[] dAVL = new int[d1.length];
				for (int i=0; i<dAVL.length; i++) {
					dAVL[i] = d1[i] - d2[i]/2;
				}
				Channel c = new Channel("aVL");
				c.setData(dAVL);
				c.setSynthetic();
				put(c);
			}
			catch (Exception unable) { }
		}
		public void makeAVF() {
			//aVF = (II + III) / 2
			//    = (II + (II - I))/2
			//    = II - I/2
			try {
				int[] d1 = get("i").data;
				int[] d2 = get("ii").data;
				int[] dAVF = new int[d1.length];
				for (int i=0; i<dAVF.length; i++) {
					dAVF[i] = d2[i] - d1[i]/2;
				}
				Channel c = new Channel("aVF");
				c.setData(dAVF);
				c.setSynthetic();
				put(c);
			}
			catch (Exception unable) { }
		}
	}
	
	static class Channel {
		String label;
		double sensitivity;
		String sensitivityUnits;
		double baseline;
		double skew;
		double offset;
		int bitsStored;
		int[] data;
		boolean synthetic = false;
		
		public Channel(Dataset ds) {
			label = getChannelLabel(ds);
			sensitivity = getFloat(ds, Tags.ChannelSensitivity, 0f);
			sensitivityUnits = getString(ds, Tags.ChannelSensitivityUnitsSeq, 0, Tags.CodeValue);
			baseline = getFloat(ds, Tags.ChannelBaseline, 0f);
			skew = getFloat(ds, Tags.ChannelSampleSkew, 0f);
			offset = getFloat(ds, Tags.ChannelOffset, 0f);
			bitsStored = getInt(ds, Tags.WaveformBitsStored, 16);
		}
		
		public Channel(String label) {
			this.label = label;
		}
		
		public String getLeadName() {
			String[] s = label.trim().split("\\s");
			return s[0].toLowerCase();
		}
		
		public void setSynthetic() {
			synthetic = true;
		}
		
		public boolean isSynthetic() {
			return synthetic;
		}
		
		public void draw(Graphics2D g2d, int width, int xOrigin, int yOrigin, double xScale, double yScale, int pixelsPerMM) {
			//draw the channel label
			g2d.setColor(Color.BLACK);
			Font font = new Font( "SansSerif", java.awt.Font.BOLD, 16 );
			g2d.setFont(font);
			float xLabel = xOrigin + 2*pixelsPerMM;
			float yLabel = yOrigin - 6*pixelsPerMM;
			String synchar = (synthetic ? " *" : "");
			g2d.drawString(label + synchar, xLabel, yLabel);
			
			//draw the waveform
			g2d.setColor(Color.BLUE);
			g2d.setStroke(new BasicStroke(2));
			for (int x=0; x<width-1; x++) {
				int x1 = (int)(x*xScale);
				int x2 = (int)((x+1)*xScale);
				x1 = Math.min(x1, data.length-1);
				x2 = Math.min(x2, data.length-1);
				int y1 = (int)(yOrigin - yScale * data[x1]);
				int y2 = (int)(yOrigin - yScale * data[x2]);
				g2d.drawLine(x+xOrigin, y1, x+1+xOrigin, y2);
			}
		}
		
		public void setData(int[] data) {
			this.data = data;
		}
		
		public String toString() {
			StringBuffer sb = new StringBuffer();
			sb.append("label:       "+label+"\n");
			sb.append("sensitivity: "+sensitivity+"\n");
			sb.append("units:       "+sensitivityUnits+"\n");
			sb.append("baseline:    "+baseline+"\n");
			sb.append("skew:        "+skew+"\n");
			sb.append("offset:      "+offset+"\n");
			sb.append("bitsStored:  "+bitsStored+"\n");
			return sb.toString();
		}
		
		private int getInt(Dataset ds, int tag, int def) {
			try { return ds.getInt(tag, def); }
			catch (Exception unable) { return def; }
		}
		private float getFloat(Dataset ds, int tag, float def) {
			try { return ds.getFloat(tag, def); }
			catch (Exception unable) { return def; }
		}
		private String getString(Dataset ds, int tag) {
			String s = null;
			try { s = ds.getString(tag); }
			catch (Exception unable) { }
			return (s != null) ? s : ""; 
		}
		private String getString(Dataset ds, int sqTag, int item, int tag) {
			String s = null;
			try { s = ds.get(sqTag).getItem(item).getString(tag); }
			catch (Exception unable) { }
			return (s != null) ? s : ""; 
		}
		private String getChannelLabel(Dataset ds) {
			String s = getString(ds, Tags.ChannelLabel);
			String ss = getString(ds, Tags.ChannelSourceSeq, 0, Tags.CodeMeaning);
			if (ss.equals("")) return ss = s;
			if (ss.startsWith("Lead ")) ss = ss.substring(5);
			return ss;
		}
				
	}
    
}
