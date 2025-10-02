import socket
from threading import Thread, Lock, Event
import queue

import av
import av.codec


class EventListener:

    def onValue(self, value : str | None):

        raise NotImplementedError("onValue not implemented")


class OpenDJI:

    
    MODULE_GIMBAL = "Gimbal"
    MODULE_REMOTECONTROLLER = "RemoteController"
    MODULE_FLIGHTCONTROLLER = "FlightController"
    MODULE_BATTERY = "Battery"
    MODULE_AIRLINK = "AirLink"
    MODULE_PRODUCT = "Product"
    MODULE_CAMERA = "Camera"

    
    PORT_VIDEO   = 9999
    PORT_CONTROL = 9998
    PORT_QUERY   = 9997

    def __init__(self, host : str):


        self.host_address = host

        
        self._socket_video = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_query = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            
            self._socket_video.connect((self.host_address, self.PORT_VIDEO))
            self._socket_control.connect((self.host_address, self.PORT_CONTROL))
            self._socket_query.connect((self.host_address, self.PORT_QUERY))
            
        except Exception as e:
            
            self._socket_video.close()
            self._socket_control.close()
            self._socket_query.close()
            raise

        

        
        self._background_frames = BackgroundVideoCodec(self._socket_video)
        self._background_control_messages = BackgroundCommandsQueue(self._socket_control)
        self._background_query_messages = BackgroundCommandListener(self._socket_query)

    

    

    
    def __enter__(self):
        return self


    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


    def close(self):
        """
        Clean after the object, closes all the communication and threads.
        """
        self._socket_video.close()
        self._socket_control.close()
        self._socket_query.close()

        self._background_frames.stop()
        self._background_control_messages.stop()
        self._background_query_messages.stop()



    

    def getFrame(self):
        """
        Retrive the latest frame available, or None if no frame available.
        """
        return self._background_frames.read()


    def frameListener(self, eventHandler : EventListener):
        """
        Set frame listener - an EventListener class that will be called on
        every new frame.

        Args:
            eventHandler (EventListener): a class that defines what to do when
                the drone receive new frame.
        """
        self._background_frames.registerListener(eventHandler)


    def removeFrameListener(self):
        """
        Remove the frame listener (if was set) by frameListener(listener) method.
        """
        self._background_frames.unregisterListener()



    

    def send_command(self, sock : socket.socket, command : str) -> None:
        """
        Sends a command over the socket, with 'TELNET' like protocol.

        Args:
            sock (socket.socket): socket to communicate over.
            command (str): string to send.
        """
        sock.send(bytes(command + '\r\n', 'utf-8'))


    def move(self, rcw : float, du : float, lr : float, bf : float, get_result: bool = False) -> str | None:
        """
        Set drone movements forces - parameters equal to control stick movement.
        All values are real numbers between -1.0 to 1.0, where 0.0 is no movement.

        Args:
            rcw (float): rotate clock wise (1.0), or anti clockwise (-1.0).
            du (float): move downward (-1.0) or upward (1.0).
            lr (float): move to the left (-1.0) or to the right (1.0).
            bf (float): move backward (-1.0) or forward (1.0).
            get_result (bool): to flag if to wait for response from the server.
        
        Return:
            Message from server (str) if get_result is true, else None.
        """
        def clip1(value):
            return min(1.0, max(-1.0, value))
        
        
        rcw = clip1(rcw)
        du = clip1(du)
        lr = clip1(lr)
        bf = clip1(bf)

        
        command = f'rc {rcw:.4f} {du:.2f} {lr:.2f} {bf:.2f}'
        self.send_command(self._socket_control, command)

        
        if get_result:
            return self._background_control_messages.read()
        else:
            self._background_control_messages.disposeNext()


    def enableControl(self, get_result: bool = False) -> str | None:
        """
        Enable the control. This command is crucial before making movements,
        as this command removes the control from the remote controller and give
        control over the drone to the application.

        Args:
            get_result (bool): to flag if to wait for response from the server.
        
        Return:
            Message from server (str) if get_result is true, else None.
        """
        self.send_command(self._socket_control, "enable")

        
        if get_result:
            return self._background_control_messages.read()
        else:
            self._background_control_messages.disposeNext()


    def disableControl(self, get_result: bool = False) -> str | None:
        """
        Disable the control. This command is crucial after controlling the
        drone, as this command removes the control from the program, and
        give it back to the remote controller.

        Args:
            get_result (bool): to flag if to wait for response from the server.
        
        Return:
            Message from server (str) if get_result is true, else None.
        """
        self.send_command(self._socket_control, "disable")

        
        if get_result:
            return self._background_control_messages.read()
        else:
            self._background_control_messages.disposeNext()


    def takeoff(self, get_result: bool = False) -> str | None:
        """
        Takeoff the drone.

        Args:
            get_result (bool): to flag if to wait for response from the server.
        
        Return:
            Message from server (str) if get_result is true, else None.
        """
        self.send_command(self._socket_control, "takeoff")

        
        if get_result:
            return self._background_control_messages.read()
        else:
            self._background_control_messages.disposeNext()


    def land(self, get_result: bool = False) -> str | None:
        """
        land the drone.

        Args:
            get_result (bool): to flag if to wait for response from the server.
        
        Return:
            Message from server (str) if get_result is true, else None.
        """
        self.send_command(self._socket_control, "land")

        
        if get_result:
            return self._background_control_messages.read()
        else:
            self._background_control_messages.disposeNext()

    

    

    def getValue(self, module : str, key : str) -> str:
        """
        Get value of a specific key.
        This method is blocking, and waits for the result.

        Args:
            module (str): the module of the key.
            key (str): the key to send the get query on.
        """
        
        return self._background_query_messages.readOnce(
            f"{module} {key}",
            f"get {module} {key}"
        )


    def listen(self, module : str, key : str, eventHandler : EventListener) -> None:
        """
        Set listener on value of a specific key.
        This method is not blocking, and once the listener is set,
        it return.

        Args:
            module (str): the module of the key.
            key (str): the key to send the get query on.
            eventHandler (EventListener): the listener to be called on new values
                of this listener. Must implement "onValue(self, value)" !
        """
        
        self._background_query_messages.setListener(
            f"{module} {key}",
            eventHandler
        )
        
        self._background_query_messages.send_command(
            f"listen {module} {key}"
        )
    

    def unlisten(self, module : str, key : str) -> None:
        """
        Remove the listener from a specific key.
        This method is blocking, and wait for the remote to answer on the request.

        Args:
            module (str): the module of the key.
            key (str): the key to send the get query on.
        """
        
        result = self._background_query_messages.readOnce(
            f"{module} {key}",
            f"unlisten {module} {key}"
        )
        
        self._background_query_messages.removeListener(
            f"{module} {key}",
        )
        return result


    def setValue(self, module : str, key : str, value : str) -> str:
        """
        Set value to a specific key.
        This method is blocking, and wait for the remote to answer on the request.

        Args:
            module (str): the module of the key.
            key (str): the key to send the get query on.
            value (str): the value to set on the desired key.
        """
        
        return self._background_query_messages.readOnce(
            f"{module} {key}",
            f"set {module} {key} {value}"
        )


    def action(self, module : str, key : str, value : None | str = None) -> str:
        """
        Send action on a spedific key.
        This method is blocking, and wait for the remote to answer on the request.
        The working principel is similar to 'set', but DJI makes the division
        between the two types.

        Args:
            module (str): the module of the key.
            key (str): the key to send the get query on.
            value (str): the value to set on the desired key.
        """
        
        if value is None:
            
            return self._background_query_messages.readOnce(
                f"{module} {key}",
                f"action {module} {key}"
            )
        
        
        else:
            
            return self._background_query_messages.readOnce(
                f"{module} {key}",
                f"action {module} {key} {value}"
            )


    def help(self, module: str | None = None, key: str | None = None) -> str:
        """
        Send a 'help' command, with or without a module name, and key.

        Args:
            module (str | None): the module name to help with,
                or None, if you want to retrieve the available modules.
            key (str | None): the key to help with,
                or None to get the key of module (if it is not None).
        """
        
        if module is None:
            return self._background_query_messages.readUnbound(
                "help"
            )
        
        
        if key is None:
            return self._background_query_messages.readUnbound(
                f"help {module}"
            )
        
        
        else:
            return self._background_query_messages.readUnbound(
                f"help {module} {key}"
            )


    def getModules(self) -> str:
        """
        Get availables modules.
        """
        return self.help()


    def getModuleKeys(self, module: str) -> str:
        """
        Get availables keys inside a module.

        Args:
            module (str): the module name to help with.
        """
        return self.help(module)


    def getKeyInfo(self, module : str, key : str) -> str:
        """
        Get information about specific key.

        Args:
            module (str): the module name to help with.
            key (str): the key name inside the module to help with.
        """
        return self.help(module, key)




class BackgroundCommandListener:
    """
    Managing all the queries from the application.
    Help with setting listeners, get values once, get message from help commands,
    both synchronously and asynchronously.
    """

    def __init__(self, sock : socket.socket):
        """
        Initiate background messages receiver from a command manager.

        Args:
            sock (socket.socket): socket receiving the messages from.
        """
        
        self._send_lock = Lock()
        self._sock = sock
        self._live = True

        
        self._listeners = {}
        self._listeners_lock = Lock()

        
        self._listeners_onces_event = {}
        self._listeners_onces_result = {}
        self._listeners_onces_lock = Lock()

        
        self._unbound_messages = queue.Queue()
        self._message = ""

        
        self._thread = Thread(target = self.__ReadMessages__)
        self._thread.daemon = True
        self._thread.start()



    def __ReadMessages__(self):
        """
        Reads messages in the background
        """
        
        
        while self._live:

            
            try:
                data = self._sock.recv(1 << 20) 
                if len(data) == 0:
                    break
            except ConnectionAbortedError:
                break

            
            
            self._message += data.decode("utf-8")

            
            messages_list = self._message.split("\r\n")
            
            
            for message in messages_list[:-1]:  

                
                
                
                if message.startswith("{") or message.count(" ") < 2:
                    self._unbound_messages.put(message)
                    continue

                
                message_parts = message.split(" ", 2)
                unique_key = message_parts[0] + " " + message_parts[1]
                message_trimed = message_parts[2]

                
                with self._listeners_onces_lock:
                    if unique_key in self._listeners_onces_event:
                        
                        self._listeners_onces_result[unique_key] = message_trimed
                        self._listeners_onces_event[unique_key].set()
                        del self._listeners_onces_event[unique_key]
                        continue

                
                with self._listeners_lock:
                    if unique_key in self._listeners:
                        
                        listener : EventListener = self._listeners[unique_key]
                        listener.onValue(message_trimed)
                        continue
                
                
                self._unbound_messages.put(message)

            
            
            self._message = messages_list[-1]
    

    def send_command(self, command : str) -> None:
        """
        Sends a command over the socket, with 'TELNET' like protocol.

        Args:
            command (str): string to send.
        """
        with self._send_lock:
            self._sock.send(bytes(command + '\r\n', 'utf-8'))


    def readOnce(self, unique_key : str, command : str) -> str:
        """
        Send a command and wait for response on the unique_key

        Args:
            unique_key (str): the key to wait for event on.
            command (str): the command to send while waiting.
        """
        event = Event()

        
        with self._listeners_onces_lock:
            
            if unique_key in self._listeners_onces_event:
                event = self._listeners_onces_event[unique_key]
            
            else:
                self._listeners_onces_event[unique_key] = event
                self.send_command(command)

        
        event.wait()
        return self._listeners_onces_result[unique_key]
    

    def readUnbound(self, command : str) -> str:
        """
        Read unbounded message but with a command.

        Args:
            command (str): the command to send while waiting.
        """
        self.send_command(command)
        return self._unbound_messages.get()
    

    def setListener(self, unique_key : str, listener : EventListener) -> None:
        """
        Register a listener for the unique_key

        Args:
            unique_key (str): the key to listen on.
            listener (EventListener): listener to register.
        """
        with self._listeners_lock:
            self._listeners[unique_key] = listener

    
    def removeListener(self, unique_key : str) -> None:
        """
        Remove listener from the list.

        Args:
            unique_key (str): the key to remove the listener from.
        """
        with self._listeners_lock:
            if unique_key in self._listeners:
                del self._listeners[unique_key]


    def stop(self, timeout : float | None = None):
        """
        Stop the thread. (Also closes the socket)

        Args:
            timeout (float | None): timeout for the operation in seconds,
                or None to wait indefenetly.
        """
        self._live = False
        self._sock.close()
        self._thread.join(timeout)









class BackgroundCommandsQueue:
    """
    Reading the return message from command server, in the background.
    Helps disposing messages and make the messages order synchronized.

    Note: this class used with the control server, which does not provide
     clear message about which command the message is associated to,
     and that may lead to misleading messages sometimes.

    Note: this class implementation does not guarante message order on multi
     threaded program. e.g. if read() and disposeNext() were called from two
     different threades, even with clear order, it is not guaranteed which
     message will be read and which disposed, as I want this class
     implementation to be as simple as posible.
     
    Hint: if one would like to implement so, you would have to use another lock,
     and to add another queue, request_orders, so the order is preserved,
     and the lock will guarante that reading from the messages queue is
     synchronized with the requests queue.
    """

    def __init__(self, sock : socket.socket):
        """
        Initiate background messages receiver from a command manager.

        Args:
            sock (socket.socket): socket receiving the messages from.
        """
        
        self._sock = sock
        self._queue = queue.Queue()
        self._live = True
        self._message = ""
        self._dispose = 0
        self._dispose_lock = Lock()

        
        self._thread = Thread(target = self.__ReadMessages__)
        self._thread.daemon = True
        self._thread.start()


    def __ReadMessages__(self):
        """
        Reads messages in the background
        """
        
        
        while self._live:

            
            try:
                data = self._sock.recv(1 << 20) 
                if len(data) == 0:
                    break
            except ConnectionAbortedError:
                break

            
            
            self._message += data.decode("utf-8")

            
            messages_list = self._message.split("\r\n")

            
            while len(messages_list) > 1 and self._dispose > 0:
                messages_list.pop(0)
                with self._dispose_lock:
                    self._dispose -= 1
            
            
            for message in messages_list[:-1]:  
                self._queue.put(message)

            
            
            self._message = messages_list[-1]
        

    def read(self, block: bool = True, timeout: float | None = None) -> str | None:
        """
        Try to read a message from the server, with blocking mechanism,
        and timeout option.

        Args:
            block (bool): True to block, false to non-block.
            timeout (float | None): set timeout to wait for message,
                or None to wait indefinitely.

        Return:
            string of the last message, if available, or None if no message.
        """
        try:
            return self._queue.get(block)
        except queue.Empty:
            self.disposeNext()
        return None


    def disposeNext(self):
        """ Set to dispose (ignore) the next received message. """
        with self._dispose_lock:
            self._dispose += 1


    def stop(self, timeout : float | None = None):
        """
        Stop the thread. (Also closes the socket)

        Args:
            timeout (float | None): timeout for the operation in seconds,
                or None to wait indefenetly.
        """
        self._live = False
        self._sock.close()
        self._thread.join(timeout)




class BackgroundVideoCodec:
    """
    Capturing the frames in the background,
    so the frame processing doesn't lag the program,
    and the most recent frame will return instantly.

    Currently retrive the frames only in H264 format.
    The drone also supports H265, but doesn't use it for now.
    If there are errors, feel free to change the codec.

    Used internally.
    """

    def __init__(self, sock : socket.socket):
        """
        Initiate background video codec, and start it right away.
        Expecting a open and connected socket to retrive the frames from.

        Args:
            sock (socket.socket): socket receiving the video from.
        """
        
        self._sock = sock
        self._frame = None
        self._codec = av.codec.context.CodecContext.create('h264', 'r')
        self._live = True
        self._listener = None

        
        self._thread = Thread(target = self.__ReadFrames__)
        self._thread.daemon = True
        self._thread.start()


    def __ReadFrames__(self):
        """
        Reads frame in the background
        """
        
        
        while self._live:

            
            try:
                data = self._sock.recv(1 << 20) 
                if len(data) == 0:
                    break
            except ConnectionAbortedError:
                break

            
            
            for packet in self._codec.parse(data):
                for frame in self._codec.decode(packet):

                    self._frame = frame.to_ndarray(format = 'bgr24')

                    
                    
                    
                    listener : EventListener = self._listener

                    if listener:
                        listener.onValue(self._frame)

        
        self._frame = None


    def read(self):
        """ Get the last available frame from this video stream. """
        return self._frame


    def stop(self, timeout : float | None = None):
        """
        Stop the thread. (Also closes the socket)

        Args:
            timeout (float | None): timeout for the operation in seconds,
                or None to wait indefenetly.
        """
        self._live = False
        self._sock.close()
        self._thread.join(timeout)


    def registerListener(self, listener : EventListener):
        """ Sets frame listener """
        self._listener = listener


    def unregisterListener(self):
        """ Remove frame listener """
        self._listener = None

