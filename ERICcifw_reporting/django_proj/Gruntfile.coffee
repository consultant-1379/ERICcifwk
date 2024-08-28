module.exports = (grunt) ->
    grunt.initConfig(
        pkg: grunt.file.readJSON('package.json')
        coffee:
            files:
                src: ['angularVis/src/js/**/*.coffee']
                dest: 'assets/js/script.js'
    )
    grunt.loadNpmTasks('grunt-contrib-coffee')
    grunt.registerTask('default', ['coffee'])
