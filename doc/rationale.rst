Rationale
=========

Analysing the execution of unknown software has become a quite complicated matter. The amount of Operating Systems and libraries to support is growing at an incredible speed. Developing and operating automated behavioural analysis platforms requires several different areas of expertise. The co-operation of such fields is critical for the effectiveness of the end product.

F-Secure developed its first prototype for an automated behavioural analysis platform in 2005. The expertise acquired over the years led to the need for a better approach in building such technologies. Rather than a single and monolithic platform trying to cover all the possible scenarios, a family of specifically tailored ones seemed a more reasonable approach for the analysis of unknown software.

Sandboxed Execution Environment has been built to enable F-Secure malware experts to quickly prototype and develop behavioural analysis engines.

The technology consists of few well known design patterns enclosed in a small framework. With SEE is possible to quickly deploy a Sandbox and attach different plugins to control it. The overall design allows to build highly flexible, robust and relatively safe platforms for test automation.
