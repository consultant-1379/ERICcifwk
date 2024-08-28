--- groupId: ${project.groupId}
--- artifactId: ${project.artifactId}
--- Version: ${project.version}
--- Type (packaging): ${project.packaging}
--- Ericsson RSTATE (version): ${ericsson.rstate}

-- Create an entry in the package table if one does not already exist
-- We assume the project.artifactId consists of packagename_packagenumber, in the
-- format:
--   ERICmyapp_CXP1234567
INSERT INTO cireports_package (name, package_number, description, signum)
VALUES ("${project.artifactId}", SUBSTRING_INDEX("${project.artifactId}", "_", -1), "${project.description}", "lciadm100") ON DUPLICATE KEY UPDATE name=name;

-- Create a revision of this package
INSERT INTO cireports_packagerevision (package_id,date_created,groupId,artifactId,version,m2type,non_proto_build,autodrop,arm_repo) VALUES
((SELECT id FROM cireports_package WHERE name = "${project.artifactId}" AND package_number = SUBSTRING_INDEX("${project.artifactId}", "_", -1)),
CURRENT_TIMESTAMP(),'${project.groupId}', '${project.artifactId}', '${project.version}', '${packaging.type}', '${enforcer.fail}', '${delivery.drop}', '${release.repo}');
