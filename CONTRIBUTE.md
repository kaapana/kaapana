## How to Contribute

First of all, we are happy about every piece of code/documentation that you contribute. Communication is key. Please coordinate your contributions ahead of time with us to minimize overhead work for both sides.

We also kindly ask to follow a few rules & guidelines:

* [Sign off your contribution](#sign-off-your-contribution) (this is a Git feature)
* Follow [the seven rules of a great Git commit message](https://chris.beams.io/posts/git-commit/)
* Split your work in easy to digest and coherent commits
* Keep reformatting of existing code to a minimum or do it in a separate commit

That said, please use [GitHub pull request](https://github.com/kaapana/kaapana/compare) for your contribution.


---
## Sign off your contribution
If you want to contribute code or documentation to Kaapana we need to ensure that you actually have the right to make that contribution. Kaapana is licensed under a [GNU Affero General Public License v3](/LICENSE) license and to be able to accept your contribution your work must be licensed under a compatible license. If you write new code or when you are allowed to re-license it, you might want to use Kaapana's license to ease integration. In case your contribution contains software patented by you, it should be licensed under the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt) license. For all contributions involving patented software, consider getting in touch with the Kaapana developers early on to discuss potential issues.

To actually certify that you have the required rights, we use the "Signed-off-by" tag appended to the log message of the patch or the tip of a Git branch containing your contribution. If you are not able to provide signed-off patches or branches, you can ask a Kaapana developer to sign off the contribution for you. For a general description of the contribution process, please read [How to contribute](#how-to-contribute). 

## Signed-off-by

The following text was taken from [linux-2.6 Documentation/SubmittingPatches](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/SubmittingPatches?id=4e8a2372f9255a1464ef488ed925455f53fbdaa1) and adapted for Kaapana.

To improve tracking of who did what, especially with patches that can percolate to their final resting place in the Medical Imaging Interaction Toolkit through several layers of maintainers, we've introduced a "sign-off" procedure on patches that are being emailed around or attached to bug reports and on Git branches requested to be merged.

The sign-off is a simple line at the end of the explanation for the patch, which certifies that you wrote it or otherwise have the right to pass it on as a open-source patch. The rules are pretty simple: if you can certify the below: 



    Developer's Certificate of Origin 1.1

    By making a contribution to this project, I certify that:

    (a) The contribution was created in whole or in part by me and I
        have the right to submit it under the open source license
        indicated in the file; or

    (b) The contribution is based upon previous work that, to the best
        of my knowledge, is covered under an appropriate open source
        license and I have the right under that license to submit that
        work with modifications, whether created in whole or in part
        by me, under the same open source license (unless I am
        permitted to submit under a different license), as indicated
        in the file; or

    (c) The contribution was provided directly to me by some other
        person who certified (a), (b) or (c) and I have not modified
        it.

    (d) I understand and agree that this project and the contribution
	are public and that a record of the contribution (including all
	personal information I submit with it, including my sign-off) is
	maintained indefinitely and may be redistributed consistent with
	this project or the open source license(s) involved.

then you just add a line saying 

	Signed-off-by: Random J Developer <random@developer.example.org>

using your real name (sorry, no pseudonyms or anonymous contributions.)

Some people also put extra tags at the end. They'll just be ignored for now, but you can do this to mark internal company procedures or just point out some special detail about the sign-off. 

## Integrating Contributions
If you are a subsystem or branch maintainer, sometimes you need to slightly modify patches you receive in order to merge them, because the code is not exactly the same in your tree and the submitters'. If you stick strictly to rule (c), you should ask the submitter to rediff, but this is a totally counter-productive waste of time and energy. Rule (b) allows you to adjust the code, but then it is very impolite to change one submitter's code and make him endorse your bugs. To solve this problem, it is recommended that you add a line between the last Signed-off-by header and yours, indicating the nature of your changes. While there is nothing mandatory about this, it seems like prepending the description with your mail and/or name, all enclosed in square brackets, is noticeable enough to make it obvious that you are responsible for last-minute changes. Example: 

    Signed-off-by: Random J Developer <random@developer.example.org>
    [lucky@maintainer.example.org: struct foo moved from foo.c to foo.h]
    Signed-off-by: Lucky K Maintainer <lucky@maintainer.example.org>

This practise is particularly helpful if you maintain a stable branch and want at the same time to credit the author, track changes, merge the fix, and protect the submitter from complaints. Note that under no circumstances can you change the author's identity (the From header), as it is the one which appears in the changelog. 

## When to use Acked-by: and Cc:
The Signed-off-by: tag indicates that the signer was involved in the development of the patch, or that he/she was in the patch's delivery path.

If a person was not directly involved in the preparation or handling of a patch but wishes to signify and record their approval of it then they can arrange to have an Acked-by: line added to the patch's changelog.

Acked-by: is often used by the maintainer of the affected code when that maintainer neither contributed to nor forwarded the patch.

Acked-by: is not as formal as Signed-off-by:. It is a record that the acker has at least reviewed the patch and has indicated acceptance. Hence patch mergers will sometimes manually convert an acker's "yep, looks good to me" into an Acked-by:.

Acked-by: does not necessarily indicate acknowledgement of the entire patch. For example, if a patch affects multiple subsystems and has an Acked-by: from one subsystem maintainer then this usually indicates acknowledgement of just the part which affects that maintainer's code. Judgement should be used here. When in doubt people should refer to the original discussion.

If a person has had the opportunity to comment on a patch, but has not provided such comments, you may optionally add a "Cc:" tag to the patch. This is the only tag which might be added without an explicit action by the person it names. This tag documents that potentially interested parties have been included in the discussion.

## Using Reported-by:, Tested-by: and Reviewed-by:
If this patch fixes a problem reported by somebody else, consider adding a Reported-by: tag to credit the reporter for their contribution. Please note that this tag should not be added without the reporter's permission, especially if the problem was not reported in a public forum. That said, if we diligently credit our bug reporters, they will, hopefully, be inspired to help us again in the future.

A Tested-by: tag indicates that the patch has been successfully tested (in some environment) by the person named. This tag informs maintainers that some testing has been performed, provides a means to locate testers for future patches, and ensures credit for the testers.

Reviewed-by:, instead, indicates that the patch has been reviewed and found acceptable according to the Reviewer's Statement: 

    Reviewer's statement of oversight

    By offering my Reviewed-by: tag, I state that:

    (a) I have carried out a technical review of this patch to
        evaluate its appropriateness and readiness for inclusion into Kaapana.

    (b) Any problems, concerns, or questions relating to the patch
        have been communicated back to the submitter.  I am satisfied
        with the submitter's response to my comments.

    (c) While there may be things that could be improved with this
        submission, I believe that it is, at this time, (1) a
        worthwhile modification to Kaapana, and (2) free of known
        issues which would argue against its inclusion.

    (d) While I have reviewed the patch and believe it to be sound, I
        do not (unless explicitly stated elsewhere) make any
        warranties or guarantees that it will achieve its stated
        purpose or function properly in any given situation.

A Reviewed-by tag is a statement of opinion that the patch is an appropriate modification of Kaapana without any remaining serious technical issues. Any interested reviewer (who has done the work) can offer a Reviewed-by tag for a patch. This tag serves to give credit to reviewers and to inform maintainers of the degree of review which has been done on the patch. Reviewed-by: tags, when supplied by reviewers known to understand the subject area and to perform thorough reviews, will normally increase the likelihood of your patch getting into Kaapana. 