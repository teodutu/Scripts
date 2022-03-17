# Lab grading

## Environment

First, you need to install a couple of packages that are listed in `requirements.txt` file.
You can install them locally by running:

```
pip3 install -r requirements.txt
```

## Configuration

In order to run the script, you need to configure some files in this folder.

Update the `course-registers.json` file and replace the strings `"TODO"` with the IDs of the registers from the courses you teach.
You can find the ID in the URL of the spreadsheet.
More information can be found [here](https://developers.google.com/sheets/api/guides/concepts).

To interact with Google API you need to generate a OAuth2.0 token.
To do this for the first time we need to create a project on the Google Cloud platform.
More information about how you can create a new project [here](https://cloud.google.com/resource-manager/docs/creating-managing-projects).

After you create the project, you must generate an OAuth2.0 token following instructions from [here](https://support.google.com/cloud/answer/6158849?hl=en).
Download the corresponding `json` format for it save it in a new file named `credentials.json`, placed in this folder.

## Running

### Arguments:

- -l/--lab <lab_number>
- -t/--ta <teaching_assistant>
- -a/--attendace <attendance_spreadsheet_id> (You can find an example of attendance list [here](https://docs.google.com/spreadsheets/d/1iK4zBbQycSV7KuMorki2ZwyexwCUSH1KgULfml8bCJk/edit?usp=sharing))
- -c/--course <course_name> (The same from the `course_registers.json`)

### Example:

Put all grades for second lab:

```
python3 grade.py -l 2 -a <attendance_spreadsheet_id> -c IOCLA
```
