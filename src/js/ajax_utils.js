function ajaxCheckPid(base, method, pid, identity, interval) {
    // base is a URL base, e.g. https://cmsweb.cern.ch
    // method is request method, e.g. /request
    // pid is DASQuery qhash
    // status request interval in seconds
    var limit = 30000; // in miliseconds
    var wait  = parseInt(interval);
    if (wait*2 < limit) {
        wait  = wait*2;
    } else if (wait==limit) {
        wait  = 5000; // initial time in msec (5 sec)
    } else { wait = limit; }
    new Ajax.Updater('response', base+'/'+method,
    { method: 'get' ,
      parameters : {'pid': pid, 'identity': identity},
      onException: function() {return;},
      onComplete : function() {
        if (url.indexOf('view=xml') != -1 ||
            url.indexOf('view=json') != -1 ||
            url.indexOf('view=plain') != -1) reload();
      },
      onSuccess : function(transport) {
        var sec = wait/1000;
        var msg = ', next check in '+sec.toString()+' sec, please wait..., <a href="/das/">stop</a> request';
        // look at transport body and match its content,
        // if check_pid still working on request, call again, otherwise
        // reload the request page
        if (transport.responseText.match(/processing PID/)) {
            transport.responseText += msg;
            setTimeout('ajaxCheckPid("'+base+'","'+method+'","'+pid+'","'+identity+'","'+wait+'")', wait);
        } else {
            reload();
        }
      }
    });
}
