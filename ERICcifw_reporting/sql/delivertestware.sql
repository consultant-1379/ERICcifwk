--- groupId: ${project.groupId}
--- artifactId: ${project.artifactId}
--- Version: ${project.version}

-- Create an entry in the testware artifact  table if one does not already exist
-- We assume the project.artifactId s in teh form testwarename_testwarenumber
 
INSERT INTO cireports_testwareartifact (name, artifact_number , description, signum)
VALUES ("${project.artifactId}", SUBSTRING_INDEX("${project.artifactId}", "_", -1), "${project.description}", "lciadm100") ON DUPLICATE KEY UPDATE name=name;

-- Create a revision of this package
INSERT INTO cireports_testwarerevision (testware_artifact_id ,date_created,version,groupId,artifactId) VALUES
((SELECT id FROM cireports_testwareartifact WHERE name = "${project.artifactId}" AND artifact_number = SUBSTRING_INDEX("${project.artifactId}", "_", -1)),
CURRENT_TIMESTAMP(), '${project.version}','${project.groupId}', '${project.artifactId}');
