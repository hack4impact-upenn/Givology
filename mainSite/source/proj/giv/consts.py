


USERNAME_MAX = 30
NAME_MAX = 50
LOC_MAX = 50


REC_STUDENT = 0
REC_PROJECT = 1

tloc = 'giv/templates/'

GENDER_CHOICES = (
    ('a', ''),
    ('m', 'Male'),
    ('f', 'Female'),
)
EDULEVELS = (
    ('1', '1st grade'),
    ('2', '2nd grade'),
    ('3', '3rd grade'),
    ('4', '4th grade'),
    ('5','5th grade'),
    ('6','6th grade'),
    ('7','7th grade'),
    ('8','8th grade'),
    ('9','9th grade'),
    ('10','10th grade'),
    ('11','11th grade'),
    ('12','12th grade'),
    ('1', '1st year, college'),
    ('2', '2nd year, college'),
    ('3', '3rd year, college'),
    ('4', '4th year, college'),
    )

COUNTRIES = (
    'Afghanistan',
    'Argentina',
    'Benin',
    'Brazil',
    'China',
    'Colombia',
    'Ecuador',
    'Ghana',
    'Guatemala',
    'Haiti',
    'India',
    'Kenya',
    'Liberia',
    'Malawi',
    'Mali',
    'Mexico',
    'Pakistan',
    'Paraguay',
    'Peru',
    'Rwanda',
    'Senegal',
    'Sri Lanka',
    'Tanzania',
    'Uganda',
    'Vietnam',
    'Zimbabwe',
    )

FATHER_OCCS = (
    'Farmer',
    'Laborer (unskilled)',
    'Craftsman (skilled)',
    'Shop owner / businessman',
    'Household',
    'Government',
    'Scientist / Engineer',
    'Deceased',
    'Unemployed',
    'Salaried Worker',
    'Other(specify)'
    )
MOTHER_OCCS = (
    'Farmer',
    'Laborer (unskilled)',
    'Craftsman (skilled)',
    'Shop owner / businesswoman',
    'Household',
    'Government',
    'Scientist / Engineer',
    'Deceased',
    'Unemployed',
    'Salaried Worker',
    'Other(specify)'
    )

KIND_CHOICES = (
    ('d', 'Donor'),
    ('s', 'Student'),
    ('p', 'Project'),
    ('o', 'Organization'),
)

YESNO_CHOICES = (
    ('y', 'Yes'),
    ('n', 'No'),
)


DONOR_GROUP_CATEGORIES = [
    'None',
    'Student',
    'Corporate',
    ]


style_dict = {
    'mainwidth'          : '895px',
    'menushift'          : '0px',
    'choicewidth'        : '120px',
    'choiceheight'       : '40px',
    'choicefontsize'     : '16px',
    'subchoicewidth'     : '80px',
    'subchoiceheight'    : '30px',
    'subchoicefontsize'  : '12px',
    'searchwidth'        : '200px',
    'searchrestultsleft' : '220px',
    'boxkinds' : [
        {'name':'genericbox',
         'color1':'e5f2ff',
         'color2':'f9fcff',
         'color3':'cfe6ff',
         'color4':'e5f2ff',
         'color5':'d2e8ff',
         'fgbgcolor':'c4e1ff',
         },
        {'name':'greenbox',
         'color1':'d0ebbd',
         'color2':'f4faef',
         'color3':'a6d983',
         'color4':'d0ebbd',
         'color5':'addc8c',
         'fgbgcolor':'92d166',
         },
        {'name':'redbox',
         'color1':'f7cece',
         'color2':'fdf3f3',
         'color3':'f1a4a4',
         'color4':'f7cece',
         'color5':'f2abab',
         'fgbgcolor':'ee8f8f',
         },
        {'name':'whitebox',
         'color1':'fff',
         'color2':'fff',
         'color3':'fff',
         'color4':'fff',
         'color5':'fff',
         'fgbgcolor':'fff',
         },
        ],
    }


banned_emails = {'linggec@gmail.com':True}


