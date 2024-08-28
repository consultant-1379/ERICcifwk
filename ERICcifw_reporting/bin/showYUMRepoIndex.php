<?php
# Directory Index (showYUMRepoIndex.php)
# #
# # Reads the YUM Repository Packages directory's content and displays it as
# # HTML. The resulting Wepage contains the YUM repos contents, including:
# # download link, creation date and size of package
# #
# # Installation:
# # Put file in YUM repo root directory, or Packages Directory but web server may not have access to this.
# # You can put file wherever you like as long as the $path variable to re declared.
#
define('SHOW_PATH', TRUE);
define('SHOW_PARENT_LINK', TRUE);
define('SHOW_HIDDEN_ENTRIES', TRUE);
function get_grouped_entries($path) {
    list($dirs, $files) = collect_directories_and_files($path);
    $dirs = filter_directories($dirs);
    $files = filter_files($files);
    return array_merge(
        array_fill_keys($dirs, TRUE),
        array_fill_keys($files, FALSE));
}

function collect_directories_and_files($path) {
    # Retrieve directories and files inside the given path.
    # Also, `scandir()` already sorts the directory entries.
    $entries = scandir($path);
    return array_partition($entries, function($entry) {
        return is_dir($entry);
    });
}

function array_partition($array, $predicate_callback) {
    # Partition elements of an array into two arrays according
    # to the boolean result from evaluating the predicate.
    $results = array_fill_keys(array(1, 0), array());
    foreach ($array as $element) {
        array_push(
            $results[(int) $predicate_callback($element)],
            $element);
    }
    return array($results[1], $results[0]);
}

function filter_directories($dirs) {
    # Exclude directories. Adjust as necessary.
    return array_filter($dirs, function($dir) {
        return $dir != '.'  # current directory
            && (SHOW_PARENT_LINK || $dir != '..') # parent directory
            && !is_hidden($dir);
    });
}

function filter_files($files) {
    # Exclude files. Adjust as necessary.
    return array_filter($files, function($file) {
        return !is_hidden($file)
            && substr($file, -4) != '.php';  # PHP scripts
    });
}

function is_hidden($entry) {
    return !SHOW_HIDDEN_ENTRIES
        && substr($entry, 0, 1) == '.'  # Name starts with a dot.
        && $entry != '.'  # Ignore current directory.
        && $entry != '..';  # Ignore parent directory.
}

function filesize_formatted($path)
{
    $size = filesize($path);
    $units = array( 'B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB');
    $power = $size > 0 ? floor(log($size, 1024)) : 0;
    return number_format($size / pow(1024, $power), 2, '.', ',') . ' ' . $units[$power];
}

# # Update $path dir to location of YUM pacakges, __DIR__ is equal to pwd of script.
$path = __DIR__ . 'PACKAGES';
# # Update the $header variable.
$header = 'HEADER YUM Repository';
$entries = get_grouped_entries($path);
?>
<!DOCTYPE html>
<html lang="de">
  <head>
    <meta charset="utf-8"/>
    <style>
      body {
        background-color: #eeeeee;
        font-family: Verdana, Arial, sans-serif;
        font-size: 90%;
        margin: 4em 0;
      }

      article,
      footer {
        display: block;
        margin: 0 auto;
        width: 480px;
      }

      a {
        color: #004466;
        text-decoration: none;
      }
      a:hover {
        text-decoration: underline;
      }
      a:visited {
        color: #666666;
      }

      article {
        background-color: #ffffff;
        border: #cccccc solid 1px;
        -moz-border-radius: 11px;
        -webkit-border-radius: 11px;
        border-radius: 11px;
        padding: 0 1em;
        width: 50%;
      }
      h1 {
        font-size: 140%;
      }
      ol {
        line-height: 1.4em;
        list-style-type: disc;
      }
      li.directory a:before {
        content: '[ ';
      }
      li.directory a:after {
        content: ' ]';
      }

      footer {
        font-size: 70%;
        text-align: center;
      }
    </style>
    <title>Directory Index</title>
  </head>
  <body>
    <article>
        <h1>Content of <?php echo SHOW_PATH ? '<em>' . $header . '</em>' : 'this directory'; ?></h1>
        <ol>
            <?php
                echo "<table cellpadding='5' cellspacing='5' border='1'>";
                //depending on your own parameters of course, but the values must be in single quotes
                echo "<tr><th>Name</th><th>Date</th><th>Size</th></tr>";
                foreach ($entries as $entry => $is_dir) {
                    $class_name = $is_dir ? 'directory' : 'file';
                    $escaped_entry = htmlspecialchars($entry);
                    $wanted_entry = $path . $escaped_entry;
                    $date = date("Y-m-d H:i:s", filemtime($wanted_entry));
                    $size = filesize_formatted($wanted_entry);
                    if ($class_name != 'directory' && strpos($escaped_entry,'.rpm') !== false){
                        echo "<tr><td><a href='$wanted_entry'>$escaped_entry</a></td><td>$date</td><td>$size</td></tr>";
                    }
                }
                echo "</table>";
            ?>
      </ol>
    </article>
  </body>
</html>
