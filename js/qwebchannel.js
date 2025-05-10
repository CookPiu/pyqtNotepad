// Copyright (C) 2016 The Qt Company Ltd.
// SPDX-License-Identifier: LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only

"use strict";

var QWebChannel = function (transport, initCallback) {
  if (typeof transport !== 'object' || typeof transport.send !== 'function') {
    console.error("The QWebChannel transport object is bogus.");
    return;
  }

  var channel = this;
  this.transport = transport;
  this.send = function (data) {
    if (typeof data !== 'string') {
      data = JSON.stringify(data);
    }
    channel.transport.send(data);
  };

  this.objects = {};
  this.execCallbacks = {};
  this.execId = 0;
  this.propertyUpdateCallbacks = {};

  this.transport.onmessage = function (message) {
    var data = message.data;
    if (typeof data === 'string') {
      data = JSON.parse(data);
    }
    switch (data.type) {
      case QWebChannel.Signal:
        channel.handleSignal(data);
        break;
      case QWebChannel.Response:
        channel.handleResponse(data);
        break;
      case QWebChannel.PropertyUpdate:
        channel.handlePropertyUpdate(data);
        break;
      default:
        console.error("invalid message received:", message.data);
        break;
    }
  };

  this.exec = function (objectName, propertyName) {
    if (++channel.execId === Number.MAX_SAFE_INTEGER) {
      channel.execId = 0;
    }
    var args = Array.prototype.slice.call(arguments, 2);
    var callback;
    if (args.length > 0 && typeof args[args.length - 1] === "function") {
      callback = args.pop();
    }

    var message = {
      type: QWebChannel.InvokeMethod,
      id: channel.execId,
      object: objectName,
      method: propertyName,
      args: args
    };

    if (!callback) {
      // Fire and forget
      channel.send(message);
      return undefined;
    }

    channel.execCallbacks[message.id] = callback;
    channel.send(message);

    return new Promise(function (resolve, reject) {
      channel.execCallbacks[message.id].promiseResolve = resolve;
      channel.execCallbacks[message.id].promiseReject = reject;
    });

  };

  this.getProperty = function (objectName, propertyName, callback) {
    var message = {
      type: QWebChannel.GetProperty,
      id: ++channel.execId,
      object: objectName,
      property: propertyName
    };
    channel.execCallbacks[message.id] = callback;
    channel.send(message);
  };

  this.setProperty = function (objectName, propertyName, value, callback) {
    var message = {
      type: QWebChannel.SetProperty,
      id: ++channel.execId,
      object: objectName,
      property: propertyName,
      value: value
    };
    channel.execCallbacks[message.id] = callback;
    channel.send(message);
  };

  this.handleSignal = function (message) {
    var object = channel.objects[message.object];
    if (object) {
      var signalName = message.signal;
      if (object[signalName]) {
        object[signalName].apply(object[signalName], message.args);
      } else {
        console.warn("Unhandled signal: " + message.object + "::" + signalName);
      }
    }
  };

  this.handleResponse = function (message) {
    if (!message.id || !channel.execCallbacks[message.id]) {
      console.error("Invalid response ID received:", message.id);
      return;
    }
    var callback = channel.execCallbacks[message.id];
    var data = message.data;

    delete channel.execCallbacks[message.id];

    if (callback.promiseResolve) {
      callback.promiseResolve(data);
    } else {
      callback(data);
    }
  };

  this.handlePropertyUpdate = function (message) {
    for (var i in message.data) {
      var data = message.data[i];
      var object = channel.objects[data.object];
      if (object) {
        var signalName = data.signal;
        if (object[signalName]) {
          object[signalName].apply(object[signalName], data.args);
        }
        // TODO: Figure out how to notify of property change without a signal
      }
    }
  };

  this.debug = function (message) {
    this.send({ type: QWebChannel.Debug, data: message });
  };

  var clientObj = {
    type: QWebChannel.Init,
    objects: []
  };

  // Register all objects, signals and properties
  for (var objectName in this.objects) {
    var object = {};
    for (var prop in this.objects[objectName]) {
      var type = typeof this.objects[objectName][prop];
      if (type === "object" && this.objects[objectName][prop] !== null && this.objects[objectName][prop].constructor.name === "Signal") {
        object[prop] = { type: "signal" };
      } else if (type === "function") {
        // TODO: Figure out how to handle functions that are not signals
      } else {
        object[prop] = { type: "property", value: this.objects[objectName][prop] };
      }
    }
    clientObj.objects.push(objectName);
    clientObj[objectName] = object;
  }

  if (initCallback) {
    this.execCallbacks[++this.execId] = function (objects) {
      for (var objectName in objects) {
        var object = objects[objectName];
        channel.objects[objectName] = new QObject(objectName, object, channel);
      }
      // Objects are ready, call initCallback.
      initCallback(channel);
    };
    this.send({ type: QWebChannel.Init, id: this.execId });
  } else {
    this.send({ type: QWebChannel.Init, id: 0 });
  }
};

QWebChannel.Signal = 1;
QWebChannel.PropertyUpdate = 2;
QWebChannel.InvokeMethod = 3;
QWebChannel.CallProperty = 4; // TODO: Remove, only used by C++
QWebChannel.GetProperty = 4; // Renamed from CallProperty
QWebChannel.SetProperty = 5;
QWebChannel.Response = 6;
QWebChannel.Init = 7;
QWebChannel.Debug = 8; // TODO: Remove, only used by C++

function QObject(name, data, webChannel) {
  this.__id__ = name;
  this.webChannel = webChannel;

  var object = this;

  // Register a QObject with methods, signals, and properties from its meta-information.
  // The meta-information is an object containing the following keys:
  //   methods: A list of method signatures.
  //   signals: A list of signal signatures.
  //   properties: A list of property names.
  //   enums: A list of enum definitions.
  //
  // Methods are directly callable on the QObject.
  // Signals are callable functions that emit the QObject's signal.
  // Properties are directly accessible via the QObject and can be changed by assignment.
  // Enums are accessible via the QObject.
  for (var name in data.methods) {
    var method = data.methods[name];
    object[method] = (function (methodName) {
      return function () {
        return object.webChannel.exec.apply(object.webChannel, [object.__id__, methodName].concat(Array.prototype.slice.call(arguments)));
      };
    }(method));
  }

  for (var name in data.signals) {
    var signal = data.signals[name];
    object[signal] = (function (signalName) {
      return function () {
        var signalArgs = arguments;
        var connections = object[signalName + "Connections"];
        if (connections) {
          connections.forEach(function (callback) {
            callback.apply(callback, signalArgs);
          });
        }
      };
    }(signal));
    object[signal + "Connect"] = (function (signalName) {
      return function (callback) {
        if (typeof callback !== 'function') {
          console.error("Bad callback given to connect to signal " + signalName);
          return;
        }
        var connections = object[signalName + "Connections"];
        if (!connections) {
          connections = object[signalName + "Connections"] = [];
        }
        connections.push(callback);
      };
    }(signal));
    object[signal + "Disconnect"] = (function (signalName) {
      return function (callback) {
        var connections = object[signalName + "Connections"];
        if (!connections) {
          return;
        }
        var idx = connections.indexOf(callback);
        if (idx !== -1) {
          connections.splice(idx, 1);
        } else {
          console.error("Cannot find connection to disconnect from signal " + signalName);
        }
      };
    }(signal));
  }

  for (var name in data.properties) {
    var property = data.properties[name];
    (function (propertyName, propertyValue) {
      Object.defineProperty(object, propertyName, {
        configurable: true,
        get: function () {
          var value = propertyValue;
          // If the property is an object, it might have been updated on the C++ side.
          // We need to query the C++ side to get the latest value.
          if (typeof value === "object") {
            // TODO: Implement property getter
          }
          return value;
        },
        set: function (value) {
          propertyValue = value;
          object.webChannel.setProperty(object.__id__, propertyName, value);
        }
      });
    }(name, property));
  }

  for (var name in data.enums) {
    var anEnum = data.enums[name];
    object[name] = anEnum;
  }
}

// If a global object already exists, use it, otherwise create a new one.
if (typeof qt !== 'object') {
  window.qt = {};
}

// Attach the QWebChannel function to the global object.
if (typeof qt.WebChannel !== 'function') {
  qt.WebChannel = QWebChannel;
}

// Make sure to export QWebChannel to the global scope if running in a CommonJS environment.
if (typeof module === 'object' && typeof module.exports === 'object') {
  module.exports = QWebChannel;
}
