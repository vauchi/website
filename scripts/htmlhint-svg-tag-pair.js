// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
//
// SPDX-License-Identifier: GPL-3.0-or-later

// Custom HTMLHint rule: tag-pair that also allows self-closing SVG elements.
// The built-in tag-pair rule only knows about HTML void elements (br, img, etc.)
// and flags valid SVG self-closing tags like <path />, <circle />, <rect /> as errors.

module.exports = function (HTMLHint) {
  HTMLHint.addRule({
    id: 'svg-tag-pair',
    description: 'Tag must be paired (with SVG void element support).',
    init(parser, reporter) {
      const stack = []

      // HTML void elements (same as built-in tag-pair)
      const htmlVoid = parser.makeMap(
        'area,base,basefont,br,col,frame,hr,img,input,isindex,link,meta,param,embed,track,command,source,keygen,wbr'
      )

      // SVG elements that are commonly self-closing
      const svgVoid = parser.makeMap(
        'path,circle,ellipse,line,rect,polygon,polyline,use,image,animate,set,animateTransform,animateMotion,stop,feGaussianBlur,feOffset,feBlend,feFlood,feComposite,feMergeNode'
      )

      parser.addListener('tagstart', (event) => {
        const tagName = event.tagName.toLowerCase()
        if (
          htmlVoid[tagName] === undefined &&
          svgVoid[tagName] === undefined &&
          !event.close
        ) {
          stack.push({
            tagName: tagName,
            line: event.line,
            col: event.col,
            raw: event.raw,
          })
        }
      })

      parser.addListener('tagend', (event) => {
        const tagName = event.tagName.toLowerCase()
        let pos
        for (pos = stack.length - 1; pos >= 0; pos--) {
          if (stack[pos].tagName === tagName) {
            break
          }
        }
        if (pos >= 0) {
          const arrTags = []
          for (let i = stack.length - 1; i > pos; i--) {
            arrTags.push(`</${stack[i].tagName}>`)
          }
          if (arrTags.length > 0) {
            const lastEvent = stack[stack.length - 1]
            reporter.error(
              `Tag must be paired, missing: [ ${arrTags.join('')} ], start tag match failed [ ${lastEvent.raw} ] on line ${lastEvent.line}.`,
              lastEvent.line || event.line,
              lastEvent.col || event.col,
              this,
              event.raw
            )
          }
          stack.length = pos
        } else {
          reporter.error(
            `Tag must be paired, no start tag: [ ${event.raw} ]`,
            event.line,
            event.col,
            this,
            event.raw
          )
        }
      })

      parser.addListener('end', (event) => {
        const arrTags = []
        for (let i = stack.length - 1; i >= 0; i--) {
          arrTags.push(`</${stack[i].tagName}>`)
        }
        if (arrTags.length > 0) {
          const lastEvent = stack[stack.length - 1]
          reporter.error(
            `Tag must be paired, missing: [ ${arrTags.join('')} ], open tag match failed [ ${lastEvent.raw} ] on line ${lastEvent.line}.`,
            event.line,
            event.col,
            this,
            ''
          )
        }
      })
    },
  })
}
