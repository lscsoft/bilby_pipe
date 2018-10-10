header = ('''
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
  <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
  <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>
</head>
<body>
''')

section_template = (''''
<div class="container">
  <h2> {title} </h2>
  <button type="button" class="btn btn-info" data-toggle="collapse" data-target="#{title}">Simple collapsible</button>
  <div id="{title}" class="collapse">
      <img src="{corner_file_path}" alt="No image available" style="width:700px;">
  </div>
</div>
''')

footer = ('''
</body>
</html>
''')


def get_section(title, corner_file_path):
    return section_template.format(
        title=title, corner_file_path=corner_file_path)

