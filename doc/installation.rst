Installation
============

Dependencies
------------

Required:
  - python
  - libvirt

Recommended:
  - qemu-kvm KVM - Kernel-based virtual machine is a full virtualization solution for Linux.
  - virtualbox Virtualbox is a full-feature virtualization solution.

\end{description}

\subsubsection{Set Up}

SEE allows to control several different virtualization technologies, according to the chosen ones the setup may vary noticeably.
In case of problems, please refer to `libvirt`'s reference documentation.

\url{http://libvirt.org/docs.html}

\begin{description}
\item[Permissions] \hfill \\

  To allow all SEE features to work properly some permission settings must be changed.

  \begin{description}
  \item[Users and groups] \hfill \\

    Add the SEE user to the libvirt group:
    \begin{verbatim}
        # adduser user libvirt
    \end{verbatim}

  \item[Disk Images Permissions] \hfill \\

    All disk images need read and write permissions to be set:
    \begin{verbatim}
        # chmod 644 disk_image_path
    \end{verbatim}

  \end{description}

\item[Hardware acceleration for virtualization (KVM Support)] \hfill \\

  To take advantages from hardware acceleration through KVM verify that the processor has VT (Intel) or SVM (AMD) capabilities and that they're enabled in the BIOS configuration.

  To verify that KVM is available it is enough to run:
  \begin{verbatim}
      # modprobe kvm
      # modprobe kvm_intel
  \end{verbatim}
  for Intel processors or:
  \begin{verbatim}
      # modprobe kvm
      # modprobe kvm_amd
  \end{verbatim}
  for AMD ones.

  If the kernel is able to load the modules then KVM is fully available.

\item[Virtualbox driver (Virtualbox Support)] \hfill \\

  To use Virtualbox ensure that its driver - `vboxdrv` - is properly loaded in the kernel.
  If not, just load it as follows:
  \begin{verbatim}
      # modprobe vboxdrv
\end{verbatim}

\item[Linux Containers (LXC Support)] \hfill \\

  Linux Containers require specific Control Groups to be enabled in order to operate:
  \begin{itemize}
  \item cpuacct
  \item memory
  \item devices
  \end{itemize}

  Additional recommended cgroups:
  \begin{itemize}
  \item cpu
  \item blkio
  \item freezer
  \end{itemize}

  To enable the required cgroups the User can rely on its init system.
  More details at:

  \url{http://libvirt.org/cgroups.html}

\end{description}
