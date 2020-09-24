package org.rsna.ctp.dkfz;

import org.rsna.ctp.plugin.AbstractPlugin;
import org.rsna.ctp.stdstages.anonymizer.dicom.AnonymizerExtension;
import org.rsna.ctp.stdstages.anonymizer.dicom.FnCall;
import org.w3c.dom.Element;

/**
 * An AnonymizerExtension.
 */
public class PseudonymizationPlugin extends AbstractPlugin implements AnonymizerExtension {
    /**
     * IMPORTANT: When the constructor is called, neither the
     * pipelines nor the HttpServer have necessarily been
     * instantiated. Any actions that depend on those objects
     * must be deferred until the start method is called.
     * @param element the XML element from the configuration file
     * specifying the configuration of the plugin.
     */
    public PseudonymizationPlugin(Element element) {
    	super(element);
    }
    /**
     * Implement the AnonymizerExtension interface
     * @param fnCall the specification of the function call.
     * @return the result of the function call.
     * @throws Exception
     */
    public String call(FnCall fnCall) throws Exception {

        //The fnCall argument contains all the information about the
        //the dataset and the element being processed, as well as the
        //arguments in the @call function in the anonymizer script.

        //The first argument must be the id attribute of the AnonymizerExtension.

        //In this example, we'll get the value of the element being processed,
        //prepend the prefix from the configuration, append the value of the
        //second argument of the fnCall, and return the result.
        return fnCall.context.cmds.getProperty("pseudonym");
    }
}