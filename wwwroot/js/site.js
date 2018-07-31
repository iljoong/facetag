var degree = { 1: 0, 3: 180, 6: 90, 8: -90 };
var fdresult = [];
var fdscale;

var mx = 0;
var my = 0;

var px = 0;
var py = 0;
var pw = 0;
var ph = 0;

var ix = 0;
var iy = 0;
var iw = 0;
var ih = 0;

$(document).ready(function (e) {

    /////////////////////////////////////////////////////////////////////////////////////////////////
    // context menu

    // return facebox number if found otherwise -1
    checkfacebox = function (row) {
        px = Math.round((mx) / fdscale);
        py = Math.round((my) / fdscale);

        fd = fdresult;
        var found = -1
        for (var i = 0; i < fd.length; i++) {
            if ((px > fd[i].rect.x && px < fd[i].rect.x + fd[i].rect.w)
                && (py > fd[i].rect.y && py < fd[i].rect.y + fd[i].rect.h)) {
                found = i;
                break;
            }
        }
        return found;
    }

    var menu = new BootstrapMenu('#facecanvas', {
        actions: [{
            name: 'Edit',
            isEnabled: function (row) {
                return checkfacebox() != -1;
            },
            onClick: function () {
                pos = checkfacebox();
                if (pos != -1) {
                    $('#edittag').val(fdresult[pos].tag)
                    $('#editpos').val(pos)
                    $('#myModal').modal('show');
                }
            }
        }, {
            name: 'Remove',
            isEnabled: function (row) {
                return checkfacebox() != -1;
            },
            onClick: function () {
                pos = checkfacebox();
                if (pos != -1) {
                    tagid = $('#tagid').val();
                    if (confirm("Do you want delete `" + fdresult[pos].tag + "`?")) {
                        $.ajax({
                            type: 'DELETE',
                            url: '/api/tag/' + tagid,
                            data: JSON.stringify({ editpos: pos }),
                            contentType: 'application/json'

                        }).done(function (data)   // A function to be called if request succeeds
                        {
                            alert(JSON.stringify(data));
                            location.reload();
                        }).fail(function (data, status) {
                            $("#loading").hide();
                            alert("Internal Error!");
                        })
                    }
                }
            }
        }]
    });

    var menu = new BootstrapMenu('.imgareaselect-border4', {
        actions: [{
            name: 'Add',
            onClick: function () {
                addface();
            }
        }, {
            name: 'Classify',
            onClick: function () {
                classifyface();
            }
        }]
    });

    addface = function () {

        facetag = $('#newfacepos').val();
        tagid = $('#tagid').val();
        console.log(facetag);

        $.ajax({
            type: 'POST',
            url: '/api/tag/' + tagid,
            data: facetag,
            contentType: 'application/json'

        }).done(function (data)   // A function to be called if request succeeds
        {
            alert(JSON.stringify(data));
            location.reload();
        }).fail(function (data, status) {
            $("#loading").hide();
            alert("Internal Error!");
        })
    }

    classifyface = function () {
        console.log(ix, iy, iw, ih);
        image_size = (iw > ih) ? iw : ih;

        var canvas = document.getElementById("facecanvas");
        var ctx = canvas.getContext('2d');
        var imgdata = ctx.getImageData(ix, iy, image_size, image_size);

        // https://stackoverflow.com/questions/13198131/how-to-save-an-html5-canvas-as-an-image-on-a-server
        var cropcanvas = document.createElement('CANVAS');
        cropcanvas.height = image_size;
        cropcanvas.width = image_size;
        ctx = cropcanvas.getContext('2d');
        ctx.putImageData(imgdata, 0, 0);
        var dataURL = cropcanvas.toDataURL();

        $.ajax({
            url: '/api/classify/face',
            type: "POST",
            data: dataURL,
            contentType: 'image/png'
        }).done(function (data)   // A function to be called if request succeeds
        {
            console.log(JSON.stringify(data));

            if (confirm("Do you want to tag as `" + data.tag + "`?")) {
                addNewFace(data.tag, data.confidence);
            } else {
                addNewFace("none", 0.0);
            }

        }).fail(function (data, status) {
            alert("Internal Error!");
        });
    }

    $("#facecanvas").mousemove(function (event) {
        mx = event.offsetX;
        my = event.offsetY;
    });

    $('#facecanvas').imgAreaSelect({
        handles: true,
        onSelectEnd: function (img, selection) {
            if (!selection.width || !selection.height) {
                return;
            }
            $('#x1').val(selection.x1);
            $('#y1').val(selection.y1);
            $('#x2').val(selection.x2);
            $('#y2').val(selection.y2);
            $('#w').val(selection.width);
            $('#h').val(selection.height);

            ix = selection.x1;
            iy = selection.y1;
            iw = selection.width;
            ih = selection.height;

            px = Math.round((selection.x1) / fdscale)
            py = Math.round((selection.y1) / fdscale);
            pw = Math.round(selection.width / fdscale)
            ph = Math.round(selection.height / fdscale);

            // make selection squared size
            isize = (pw > ph) ? pw : ph

            var newtag = { tag: "none", confidence: 0.0, rect: { x: px, y: py, w: isize, h: isize } };
            $('#newfacepos').val(JSON.stringify(newtag));
        }
    });

    // face recognition
    // https://www.formget.com/ajax-image-upload-php/
    $("#uploadimage").on('submit', (function (e) {

        var api = "/api/classify";

        $("#message").empty();
        $("#loading").show();
        var canvas = document.getElementById("preview");
        var ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, 1000, 1000);

        e.preventDefault();

        $.ajax({
            url: api,          // Url to which the request is send
            type: "POST",             // Type of request to be send, called as method
            data: new FormData(this), // Data sent to server, a set of key/value pairs (i.e. form fields and values)
            contentType: false,       // The content type used when sending data to the server.
            cache: false,             // To unable request pages to be cached
            processData: false,        // To send DOMDocument or non processed data file it is set to false
        }).done(function (data)   // A function to be called if request succeeds
        {
            $("#loading").hide();

            var d = JSON.parse(data);
            var fd = d.detect;

            if (confirm("Upload completed!\nDo you want to edit? Click 'Yes' to move edit page")) {
                location.replace('/edit/' + d._id);
            } else {

                // show result
                $("#message").html(data);
                $("#tagid").val(d._id);

                var img = document.getElementById("faceimg");
                var scale = 1.0;
                if (img.height > 1000 || img.width > 1000) {
                    scale = 1000.0 / ((img.height > img.width) ? img.height : img.width);
                }

                fdresult = fd;
                fdscale = scale;

                var preview = document.getElementById("preview");
                // 1 = 0, 3 = 180, 6 = 90, 8 = -90(270)
                roateImage(preview, degree[d.rotation], fdresult, fdscale);
            }
        }).fail(function (data, status) {
            $("#loading").hide();
            alert("Internal Error!");
        });
    }));

    $("#file").change(function () {
        readURL(this);
    });

    $('.NO-CACHE').attr('src', function () { return $(this).attr('src') + "?a=" + Math.random() });
});

function addNewFace(tag, conf) {

    isize = (pw > ph) ? pw : ph

    var facetag = { tag: tag, confidence: conf, rect: { x: px, y: py, w: isize, h: isize } };
    tagid = $('#tagid').val();
    console.log(facetag);

    $.ajax({
        type: 'POST',
        url: '/api/tag/' + tagid,
        data: JSON.stringify(facetag),
        contentType: 'application/json'
    }).done(function (data)   // A function to be called if request succeeds
    {
        //alert(JSON.stringify(data));
        location.reload();
    }).fail(function (data, status) {
        $("#loading").hide();
        alert("Internal Error!");
    })
}

function readURL(input) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();

        reader.onload = function (e) {
            $('#faceimg').attr('src', e.target.result);
        };
        reader.readAsDataURL(input.files[0]);
    }
}

function editLoaded(id, fd, rotation) {

    var img = document.getElementById("faceimg");
    var scale = 1.0;
    if (img.height > 1000 || img.width > 1000) {
        scale = 1000.0 / ((img.height > img.width) ? img.height : img.width);
    }

    fdresult = fd;
    fdscale = scale;

    var canvas = document.getElementById("facecanvas");
    roateImage(canvas, degree[rotation], fdresult, fdscale);
}

// https://stackoverflow.com/questions/17411991/html5-canvas-rotate-image
function roateImage(canvas, degree, fdresult, fdscale) {
    //var canvas = document.getElementById("facecanvas");
    var fd = fdresult;
    var scale = fdscale;

    var img = document.getElementById("faceimg");
    var ctx = canvas.getContext('2d');

    if (degree == 0 || degree == 180) {
        canvas.width = img.width * scale;
        canvas.height = img.height * scale;
    } else {
        canvas.height = img.width * scale;
        canvas.width = img.height * scale;
    }

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate(degree * Math.PI / 180);
    ctx.drawImage(img,  -(img.width * scale) / 2, -(img.height * scale) / 2, img.width * scale, img.height * scale);

    //console.log("x:", -(img.width * scale)/2, "y:", -(img.height * scale)/2);
    ctx.restore();

    ctx.beginPath();
    ctx.lineWidth = "3";
    ctx.strokeStyle = "red";

    //console.log("offsetx", offsetx, "offsety", offsety);
    for (var i = 0; i < fd.length; i++) {
        ctx.rect(fd[i].rect.x * scale, fd[i].rect.y * scale, fd[i].rect.w * scale, fd[i].rect.h * scale);
        if (fd[i].tag) {
            ctx.font = "20px Arial";
            ctx.fillStyle = "black";
            ctx.fillText(fd[i].tag + ", " + fd[i].confidence.toFixed(2),
                fd[i].rect.x * scale+ 2, fd[i].rect.y * scale - 3);
            ctx.font = "20px Arial";
            ctx.fillStyle = "white";
            ctx.fillText(fd[i].tag + ", " + fd[i].confidence.toFixed(2),
                fd[i].rect.x * scale, fd[i].rect.y * scale - 5);
        }
        ctx.stroke();
    }
}

/*
function roateImage(canvas, degree, fdresult, fdscale) {
    //var canvas = document.getElementById("facecanvas");
    var img = document.getElementById("faceimg");
    var ctx = canvas.getContext('2d');

    ctx.save();

    var fd = fdresult;
    var scale = fdscale;
    ctx.clearRect(0, 0, 1000, 1000);
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate(degree * Math.PI / 180);
    ctx.drawImage(img, -(img.width * scale) / 2, -(img.height * scale) / 2, img.width * scale, img.height * scale);

    //console.log("x:", -(img.width * scale)/2, "y:", -(img.height * scale)/2);

    ctx.restore();

    ctx.beginPath();
    ctx.lineWidth = "3";
    ctx.strokeStyle = "red";

    var offsetx = (img.width * scale < 1000) ? (canvas.width - (img.width * scale)) / 2 : 0;
    var offsety = (img.height * scale < 1000) ? (canvas.height - (img.height * scale)) / 2 : 0;
    if (degree == 90 || degree == -90) {
        offsetx = (img.height * scale < 1000) ? (canvas.height - (img.height * scale)) / 2 : 0;
        offsety = (img.width * scale < 1000) ? (canvas.width - (img.width * scale)) / 2 : 0;
    }

    //console.log("offsetx", offsetx, "offsety", offsety);
    for (var i = 0; i < fd.length; i++) {
        ctx.rect(fd[i].rect.x * scale + offsetx, fd[i].rect.y * scale + offsety, fd[i].rect.w * scale, fd[i].rect.h * scale);
        if (fd[i].tag) {
            ctx.font = "20px Arial";
            ctx.fillStyle = "black";
            ctx.fillText(fd[i].tag + ", " + fd[i].confidence.toFixed(2),
                fd[i].rect.x * scale + offsetx + 2, fd[i].rect.y * scale + offsety - 3);
            ctx.font = "20px Arial";
            ctx.fillStyle = "white";
            ctx.fillText(fd[i].tag + ", " + fd[i].confidence.toFixed(2),
                fd[i].rect.x * scale + offsetx, fd[i].rect.y * scale + offsety - 5);
        }
        ctx.stroke();
    }
    offx = offsetx;
    offy = offsety;
}
*/
