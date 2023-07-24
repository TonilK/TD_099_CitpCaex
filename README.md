# CITP CAEX component. 
Beta v.0.3. TD build: 64-bit 2018.27840. Capture ver 24.1.22 Demo

## Description:
The component is designed to transmit data via the CITP CAEX protocol to the Capture visualization software. Two channels are used for communication - UDP and TCP. UDP is used for establishing a connection and streaming data, while TCP is used for configuring CAEX parameters.

## General working principle:
1. A multicast UDP connection is opened, and the component waits to receive CITP messages from Capture, specifying the port on which Capture expects the TCP connection.
2. If the corresponding message is received, a TCP connection is established, and the CAEX configuration begins.
3. The CAEX configuration involves the component informing Capture about the session ID - this is the source code parameter, which will later be used to stream laser data via the UDP connection. Apparently, this ID helps Capture coordinate data from these two channels - TCP and UDP.
4. Then, a list of all feeds and their names is sent, and Capture assigns them numbers and sends them back as a response.
5. Capture also sends its status of readiness to receive laser data - this status is encapsulated in the FrameRate parameter (see CAEX spec LaserFeedControl message). If the FrameRate is 0, it means that the stream should be stopped, if not, it specifies the required FrameRate. In the component, this number is displayed in the read-only parameter *Required Fps.* **IMPORTANT**. The FPS of the TD project must be set as the value in the "Required Fps" parameter of the component.
6. The data streaming starts through the opened UDP connection. The component collects input data for each frame and packs them according to the CAEXLaserFeedFrame message format.
