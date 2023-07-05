/* zephyr/1.0 chrifren@ifi.uio.no 4-july-2023 */

let dropArea = document.getElementById('drop-area')

;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false)
})

function preventDefaults (e) {
    e.preventDefault()
    e.stopPropagation()
}

;['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, highlight, false)
})

;['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, unhighlight, false)
})

function highlight(e) {
    dropArea.classList.add('highlight')
}

function unhighlight(e) {
    dropArea.classList.remove('highlight')
}

function handleFiles(files) {
    ([...files]).forEach(uploadFile)
}

function uploadFile(file) {
    // get the url to upload to from the server /api/get-token?fn=filename endpoint
    fetch('/api/get-token?fn=' + file.name).then(response => {
        response.json().then(data => {
            console.log(data.uri)
            // now upload the real file
            let url = data.uri
            
            fetch(url, {
                method: 'PUT',
                headers: {
                    'x-ms-blob-type': 'BlockBlob',
                    'x-ms-version': '2019-12-12', // or your specific version
                    'Content-Type': file.type,
                    'x-ms-meta-original_filename': file.name,
                    'x-ms-meta-original_date': new Date(file.lastModified).toISOString(),
                    'x-ms-meta-upload_agent': 'zephyr-webui',
                },
                body: file
            })
            .then(() => { /* Done. Inform the user */ })
            .catch(() => { /* Error. Inform the user */ })
        })
    })
}

dropArea.addEventListener('drop', handleDrop, false)

function handleDrop(e) {
    let dt = e.dataTransfer
    let files = dt.files
    
    handleFiles(files)
}